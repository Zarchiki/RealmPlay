"""Built-in llama.cpp / llama-server process manager for RealmPlay.
Provides local GGUF inference using llama-server.exe.
"""
import atexit
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.request
from typing import Dict, List, Optional

log = logging.getLogger("realmplay.engine")
DEFAULT_ENGINE_PORT = 5006
ORIGIN = f"http://127.0.0.1:{DEFAULT_ENGINE_PORT}"


class TextEngine:
    def __init__(self, root_dir: str = None, fallback_dir: str = None):
        self.root = Path(root_dir or os.path.dirname(os.path.abspath(__file__))).resolve()
        self.fallback_root = Path(fallback_dir).resolve() if fallback_dir and os.path.exists(fallback_dir) else None
        self.process: Optional[subprocess.Popen] = None
        self.current_model: str = ""
        self.settings: dict = {}
        self.started: float = 0
        self.error: str = ""
        self.lock = threading.RLock()
        self.job = None
        self.port = DEFAULT_ENGINE_PORT

        self.log_dir = self.root / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.log_path = self.log_dir / "builtin-llm-engine.log"

        atexit.register(self.stop)

    def get_server_exe(self) -> Optional[Path]:
        """Locates llama-server.exe in RealmPlay runtime or root folder."""
        candidates = [
            self.root / "runtime" / "llama" / "llama-server.exe",
            self.root / "runtime" / "llama-server.exe",
            self.root / "llama-server.exe",
        ]
        if self.fallback_root:
            candidates.append(self.fallback_root / "runtime" / "llama" / "llama-server.exe")

        for exe in candidates:
            if exe.is_file():
                return exe
        return None

    def get_model_directories(self) -> List[Path]:
        """Collects candidate directories containing GGUF models."""
        dirs = [
            self.root / "models",
            self.root / "models" / "text",
        ]
        # Check config.json extra paths if present
        try:
            cfg_path = self.root / "config.json"
            if cfg_path.is_file():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    extra = cfg.get("extra_model_paths", {})
                    for k in ("text_models", "aurelia_text_models"):
                        if k in extra and os.path.isdir(extra[k]):
                            dirs.append(Path(extra[k]).resolve())
        except Exception as e:
            log.warning(f"Failed parsing extra_model_paths: {e}")

        if self.fallback_root:
            dirs.append((self.fallback_root / "model_dir" / "text").resolve())

        # Filter unique existing directories
        valid_dirs = []
        for d in dirs:
            if d.is_dir() and d not in valid_dirs:
                valid_dirs.append(d)
        return valid_dirs

    def get_vision_directories(self) -> List[Path]:
        """Collects candidate directories containing vision projector GGUF models."""
        dirs = [
            self.root / "models" / "vision",
            self.root / "models",
        ]
        # Check config.json extra paths if present
        try:
            cfg_path = self.root / "config.json"
            if cfg_path.is_file():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    extra = cfg.get("extra_model_paths", {})
                    for k in ("vision_models", "aurelia_vision_models"):
                        if k in extra and os.path.isdir(extra[k]):
                            dirs.append(Path(extra[k]).resolve())
        except Exception as e:
            log.warning(f"Failed parsing extra_model_paths for vision: {e}")

        if self.fallback_root:
            dirs.append((self.fallback_root / "model_dir" / "vision").resolve())

        valid_dirs = []
        for d in dirs:
            if d.is_dir() and d not in valid_dirs:
                valid_dirs.append(d)
        return valid_dirs

    def list_vision_models(self) -> List[Dict[str, str]]:
        """Scans for mmproj vision model files."""
        models = []
        seen = set()
        for folder in self.get_vision_directories():
            for p in folder.rglob("*.gguf"):
                if p.name not in seen:
                    seen.add(p.name)
                    size_mb = round(p.stat().st_size / (1024**2), 1)
                    models.append({
                        "filename": p.name,
                        "path": str(p.resolve()),
                        "size": f"{size_mb} MB",
                        "folder": folder.name
                    })
        return models

    def find_vision_path(self, mmproj_name: str) -> Optional[Path]:
        """Finds full path for a given vision projector filename."""
        if not mmproj_name:
            return None
        direct = Path(mmproj_name)
        if direct.is_file() and direct.suffix.lower() == ".gguf":
            return direct
        for folder in self.get_vision_directories():
            target = folder / mmproj_name
            if target.is_file():
                return target
            for p in folder.rglob("*.gguf"):
                if p.name == mmproj_name:
                    return p
        return None

    def list_models(self) -> List[Dict[str, str]]:
        """Scans all configured directories for .gguf files."""
        models = []
        seen = set()
        for folder in self.get_model_directories():
            for p in folder.rglob("*.gguf"):
                # Exclude mmproj from text models
                if "mmproj" in p.name.lower():
                    continue
                if p.name not in seen:
                    seen.add(p.name)
                    size_gb = round(p.stat().st_size / (1024**3), 2)
                    models.append({
                        "filename": p.name,
                        "path": str(p.resolve()),
                        "size": f"{size_gb} GB",
                        "folder": folder.name
                    })
        return models

    def find_model_path(self, model_name: str) -> Optional[Path]:
        """Finds full path for a given model filename."""
        if not model_name:
            return None
        # Check direct path
        direct = Path(model_name)
        if direct.is_file() and direct.suffix.lower() == ".gguf":
            return direct

        for folder in self.get_model_directories():
            target = folder / model_name
            if target.is_file():
                return target
            for p in folder.rglob("*.gguf"):
                if p.name == model_name:
                    return p
        return None

    def build_command(self, model_path: Path, mmproj_path: Optional[Path] = None, context: int = 8192, gpu_layers: int = 99, threads: int = 8, batch_size: int = 512, cache_type_k: str = "q8_0", cache_type_v: str = "q8_0") -> List[str]:
        exe = self.get_server_exe()
        if not exe:
            raise FileNotFoundError("Could not find llama-server.exe in RealmPlay runtime or root folder")

        command = [
            str(exe),
            "--model", str(model_path),
            "--alias", "builtin",
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--ctx-size", str(context),
            "--gpu-layers", str(gpu_layers),
            "--threads", str(threads),
            "--batch-size", str(batch_size),
            "--ubatch-size", str(min(batch_size, 512)),
            "--cache-type-k", cache_type_k,
            "--cache-type-v", cache_type_v,
            "--parallel", "1",
            "--jinja",
            "--no-ui",
            "--reasoning", "off",
            "--reasoning-budget", "0"
        ]
        if mmproj_path and mmproj_path.is_file():
            command += ["--mmproj", str(mmproj_path)]
        return command

    def start(self, model_name: str, mmproj: Optional[str] = None, context: int = 8192, gpu_layers: int = 99, threads: int = 8, batch_size: int = 512, cache_type_k: str = "q8_0", cache_type_v: str = "q8_0"):
        with self.lock:
            model_path = self.find_model_path(model_name)
            if not model_path:
                raise ValueError(f"Model file '{model_name}' not found in any model directories")

            mmproj_path = self.find_vision_path(mmproj) if mmproj else None

            command = self.build_command(model_path, mmproj_path=mmproj_path, context=context, gpu_layers=gpu_layers, threads=threads, batch_size=batch_size, cache_type_k=cache_type_k, cache_type_v=cache_type_v)

            self.stop()

            # Verify port isn't busy
            with socket.socket() as sock:
                sock.settimeout(0.3)
                if sock.connect_ex(("127.0.0.1", self.port)) == 0:
                    raise ValueError(f"Port {self.port} is already in use by another process")

            self.error = ""
            self.current_model = model_name
            self.settings = {
                "model": model_name,
                "mmproj": mmproj if mmproj_path else "",
                "context": context,
                "gpu_layers": gpu_layers,
                "threads": threads,
                "batch_size": batch_size,
                "cache_type_k": cache_type_k,
                "cache_type_v": cache_type_v,
            }
            self.started = time.monotonic()

            runtime_dir = model_path.parent
            with self.log_path.open("ab") as output:
                output.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Launching {model_name} (Vision: {mmproj or 'None'})\n".encode())
                output.flush()
                self.process = subprocess.Popen(
                    command,
                    cwd=str(self.root),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )

            # Assign Windows Kill-On-Close Job Object if possible so it exits with parent
            if os.name == "nt":
                try:
                    import sys
                    root_str = str(self.root)
                    if root_str not in sys.path:
                        sys.path.insert(0, root_str)
                    from windows_job import create_kill_on_close_job, assign_pid
                    if self.job is None:
                        self.job = create_kill_on_close_job()
                    assign_pid(self.job, self.process.pid)
                except Exception as e:
                    log.warning(f"Could not assign job object to process {self.process.pid}: {e}")

            log.info("Built-in LLM process started with PID %s (Model: %s, Vision: %s)", self.process.pid, model_name, mmproj)
            return self.status()

    def stop(self):
        with self.lock:
            proc = self.process
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
                log.info("Built-in LLM process stopped")
            self.process = None
            self.current_model = ""

    def status(self) -> dict:
        with self.lock:
            state = "stopped"
            if self.process is not None:
                if self.process.poll() is not None:
                    state = "error"
                    self.error = f"Engine process exited unexpectedly with code ({self.process.returncode}). Check logs/builtin-llm-engine.log"
                else:
                    state = "loading"
                    try:
                        req = urllib.request.Request(f"{ORIGIN}/health")
                        with urllib.request.urlopen(req, timeout=0.4) as resp:
                            if resp.status == 200:
                                state = "ready"
                    except Exception:
                        if time.monotonic() - self.started > 180:
                            self.stop()
                            self.error = "Model loading timed out after 180s. Check logs/builtin-llm-engine.log"
                            state = "error"
            elif self.error:
                state = "error"

            has_vision = bool(self.settings.get("mmproj"))
            return {
                "state": state,
                "model": self.current_model,
                "vision": has_vision,
                "mmproj": self.settings.get("mmproj", ""),
                "port": self.port,
                "settings": self.settings,
                "error": self.error,
                "api_url": f"{ORIGIN}/v1"
            }


# Singleton instance
built_in_engine = TextEngine()
