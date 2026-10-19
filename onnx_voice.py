"""RVC ONNX adapter for the existing HuBERT/pitch/audio pipeline."""
import json
from pathlib import Path
import sys

import numpy as np
import torch

# Keep the ONNX dependency separate from Oobabooga's managed environment.
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime_packages"))
import onnxruntime as ort


class OnnxVoice:
    def __init__(self, path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=options,
                                            providers=["CPUExecutionProvider"])
        self.inputs = {item.name: item for item in self.session.get_inputs()}
        metadata = self.session.get_modelmeta().custom_metadata_map
        self.metadata = json.loads(metadata.get("metadata", "{}"))
        # Support sidecar JSON: params.json, <name>_params.json, or <name>.json
        p_path = Path(path)
        sidecar_candidates = [
            p_path.with_name("params.json"),
            p_path.with_name(f"{p_path.stem}_params.json"),
            p_path.with_name(f"{p_path.stem}.json"),
        ]
        for sidecar in sidecar_candidates:
            if sidecar.is_file():
                try:
                    self.metadata = {**json.loads(sidecar.read_text(encoding="utf-8-sig")), **self.metadata}
                    break
                except Exception as e:
                    print(f"[OnnxVoice] Warning reading sidecar {sidecar.name}: {e}")
        channels = self.metadata.get("embChannels")
        self.version = {256: "v1", 768: "v2"}.get(channels)
        expected_layer = 9 if self.version == "v1" else 12
        if (self.version is None or self.metadata.get("embedder") != "hubert_base"
                or self.metadata.get("embOutputLayer") != expected_layer
                or self.metadata.get("useFinalProj") != (self.version == "v1")):
            raise ValueError("Unsupported ONNX voice: expected RVC v1/v2 with hubert_base metadata")
        self.sample_rate = self.metadata.get("samplingRate")
        if self.sample_rate not in (32000, 40000, 48000):
            raise ValueError("Unsupported ONNX voice sample rate")
        self.f0 = self.metadata.get("f0")
        expected = {"feats", "p_len", "sid"} | ({"pitch", "pitchf"} if self.f0 else set())
        if set(self.inputs) != expected:
            raise ValueError(f"Unsupported ONNX input layout: {sorted(self.inputs)}")
        if self.inputs["feats"].shape[-1] != channels:
            raise ValueError("ONNX feature dimensions disagree with model metadata")
        if "audio" not in {item.name for item in self.session.get_outputs()}:
            raise ValueError("ONNX model has no audio output")

    def infer(self, feats, p_len, *args):
        values = {"feats": feats, "p_len": p_len}
        if self.f0:
            values.update(zip(("pitch", "pitchf", "sid"), args))
        else:
            values["sid"] = args[0]
        types = {"tensor(float16)": np.float16, "tensor(float)": np.float32,
                 "tensor(int64)": np.int64, "tensor(int32)": np.int32}
        feed = {}
        for name, spec in self.inputs.items():
            if spec.type not in types:
                raise ValueError(f"Unsupported ONNX input type: {spec.type}")
            feed[name] = np.ascontiguousarray(values[name].detach().cpu().numpy(), dtype=types[spec.type])
        # Exported voices also expose training tensors; request only audio.
        audio = self.session.run(["audio"], feed)[0].astype(np.float32)
        if audio.ndim != 3 or audio.shape[:2] != (1, 1) or not np.isfinite(audio).all():
            raise ValueError("ONNX voice returned invalid audio")
        return (torch.from_numpy(audio),)


def load_onnx_voice(rvc, path):
    from rvc_python.modules.vc.pipeline import Pipeline

    voice = OnnxVoice(path)
    vc = rvc.vc
    vc.tgt_sr = voice.sample_rate
    vc.if_f0 = int(bool(voice.f0))
    vc.version = voice.version
    vc.net_g = voice
    vc.pipeline = Pipeline(vc.tgt_sr, rvc.config, lib_dir=rvc.lib_dir)
    rvc.current_model = Path(path).name
    rvc.models[rvc.current_model] = {"pth": str(path), "index": ""}
    rvc.f0up_key = int(voice.metadata.get("defaultTune", 0))
    rvc.protect = float(voice.metadata.get("defaultProtect", 0.33))
