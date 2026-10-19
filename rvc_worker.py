import argparse
import faulthandler
import json
import os
from pathlib import Path
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--device", default=os.getenv("AURELIA_RVC_DEVICE", "cpu"))
parser.add_argument("--pitch", type=int, default=0, help="Pitch shift in semitones (f0_up_key)")
parser.add_argument("--index", default="", help="Path to feature retrieval .index file or 'none'")
parser.add_argument("--index-rate", type=float, default=None, help="Feature retrieval index rate (0.0 to 1.0)")
parser.add_argument("--protect", type=float, default=None, help="Protect voiceless consonants (0.0 to 0.5)")
args = parser.parse_args()
faulthandler.dump_traceback_later(60, repeat=False)

if args.device.startswith("cpu"):
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ[key] = "1"
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)

# --- MONKEYPATCH FOR PYTHON 3.11 + FAIRSEQ ---
import dataclasses
_original_field = dataclasses.field
def _patched_field(*args, **kwargs):
    if 'default' in kwargs and hasattr(kwargs['default'], '__dataclass_fields__'):
        cls = type(kwargs['default'])
        if cls.__hash__ is None:
            cls.__hash__ = object.__hash__
    return _original_field(*args, **kwargs)
dataclasses.field = _patched_field
# ---------------------------------------------

from rvc_python.infer import RVCInference
import rvc_python.infer as inference_module
import torch
faulthandler.enable()
dataclasses.field = _original_field

# Keep mutable RVC configuration and assets in this app, not Oobabooga's env.
runtime = Path(__file__).resolve().parent / "rvc_runtime"
inference_module.__file__ = str(runtime / "infer.py")

def _check_assets(lib_dir):
    if not (Path(lib_dir) / "base_model" / "hubert_base.pt").is_file():
        raise FileNotFoundError("Missing rvc_runtime/base_model/hubert_base.pt")

inference_module.download_rvc_models = _check_assets

if args.device.startswith("cpu"):
    def _cpu_config(lib_dir, device):
        return SimpleNamespace(device="cpu", is_half=False, x_pad=1,
                               x_query=6, x_center=38, x_max=41)
    inference_module.Config = _cpu_config

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
voice_root = Path(__file__).resolve().parent / "model_dir" / "voice"
rvc = RVCInference(models_dir=str(voice_root if voice_root.is_dir() else voice_root.parent), device=args.device)
model_path = Path(args.model).resolve()
model_dir = model_path.parent
stem = model_path.stem

# Discover sidecar params JSON
sidecar_params = {}
sidecar_candidates = [
    model_dir / "params.json",
    model_dir / f"{stem}_params.json",
    model_dir / f"{stem}.json",
]
for sc in sidecar_candidates:
    if sc.is_file():
        try:
            sidecar_params = json.loads(sc.read_text(encoding="utf-8-sig"))
            print(f"[RVC Worker] Loaded sidecar parameters from {sc.name}")
            break
        except Exception as e:
            print(f"[RVC Worker] Error reading {sc.name}: {e}")

# Discover matching index file
index_path = ""
if args.index:
    if args.index.lower() == "none":
        index_path = ""
    else:
        direct_cand = Path(args.index)
        if direct_cand.is_file():
            index_path = str(direct_cand.resolve())
        elif (model_dir / direct_cand.name).is_file():
            index_path = str((model_dir / direct_cand.name).resolve())

if not index_path and args.index.lower() != "none":
    configured_index = sidecar_params.get("indexFile")
    if configured_index:
        cand = model_dir / configured_index
        if not cand.is_file() and (model_dir / Path(configured_index).name).is_file():
            cand = model_dir / Path(configured_index).name
        if cand.is_file():
            index_path = str(cand)

    if not index_path:
        # Auto-detect .index files in same folder matching stem or any .index
        matching_indexes = list(model_dir.glob(f"{stem}*.index"))
        if matching_indexes:
            index_path = str(matching_indexes[0])
        else:
            # Fallback to single index file in directory if only one exists
            all_indexes = list(model_dir.glob("*.index"))
            if len(all_indexes) == 1:
                index_path = str(all_indexes[0])

if index_path:
    print(f"[RVC Worker] Using index file: {os.path.basename(index_path)}")
else:
    print("[RVC Worker] No index file used")

if model_path.suffix.lower() == ".onnx":
    from onnx_voice import load_onnx_voice
    load_onnx_voice(rvc, str(model_path))
else:
    checkpoint = torch.load(str(model_path), map_location="cpu", weights_only=True)
    version = checkpoint.get("version")
    if version not in ("v1", "v2"):
        version = "v1" if checkpoint["weight"]["enc_p.emb_phone.weight"].shape[1] == 256 else "v2"
    del checkpoint
    rvc.load_model(str(model_path), version=version, index_path=index_path)

# Determine tuning and params: command line overrides take precedence, fallback to params.json defaults
tune = args.pitch if args.pitch != 0 else int(sidecar_params.get("defaultTune", 0))

if args.index_rate is not None:
    index_rate = float(args.index_rate)
else:
    index_rate = float(sidecar_params.get("defaultIndexRatio", 0.75 if index_path else 0.0))

if args.protect is not None:
    protect = float(args.protect)
else:
    protect = float(sidecar_params.get("defaultProtect", 0.33))

rvc.set_params(f0up_key=tune, index_rate=index_rate, protect=protect)
print(f"[RVC Worker] Generation parameters -> pitch/tune: {tune}, index_rate: {index_rate}, protect: {protect}")

rvc.infer_file(args.input, args.output)
faulthandler.cancel_dump_traceback_later()
