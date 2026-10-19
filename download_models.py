"""Download script for RealmPlay default models and llama-server.
Usage:
    python download_models.py
"""
import os
import sys
import urllib.request
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MODELS = [
    {
        "name": "Qwen3.5-4B Uncensored (Aggressive) GGUF",
        "url": "https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/resolve/main/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf",
        "dest": BASE_DIR / "models" / "text" / "Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf",
        "size_str": "~2.6 GB"
    },
    {
        "name": "Qwen3.5-4B Vision mmproj (Multimodal)",
        "url": "https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/resolve/main/mmproj-Qwen3.5-4B-mmproj-BF16.gguf",
        "dest": BASE_DIR / "models" / "vision" / "mmproj-Qwen3.5-4B-mmproj-BF16.gguf",
        "size_str": "~645 MB"
    }
]

def reporthook(count, block_size, total_size):
    if total_size > 0:
        percent = int(count * block_size * 100 / total_size)
        downloaded_mb = (count * block_size) / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  Progress: [{percent:3d}%] {downloaded_mb:.1f} MB / {total_mb:.1f} MB")
        sys.stdout.flush()

def download_file(item):
    dest = Path(item["dest"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    if dest.exists() and dest.stat().st_size > 1000000:
        print(f"[OK] Already exists: {dest.name}")
        return

    print(f"\n[Downloading] {item['name']} ({item['size_str']})")
    print(f"Destination: {dest}")
    temp_dest = dest.with_suffix(".tmp")
    
    try:
        urllib.request.urlretrieve(item["url"], temp_dest, reporthook)
        print()
        if temp_dest.exists():
            temp_dest.replace(dest)
            print(f"[Done] Saved to {dest}")
    except Exception as e:
        print(f"\n[Error] Download failed: {e}")
        if temp_dest.exists():
            try:
                temp_dest.unlink()
            except Exception:
                pass

def main():
    print("=" * 60)
    print("      RealmPlay Model Downloader (Hugging Face)")
    print("=" * 60)
    print("This script downloads recommended AI models for RealmPlay Standalone.")
    print("Make sure you have an active internet connection.\n")

    for m in MODELS:
        download_file(m)

    print("\n" + "=" * 60)
    print("All downloads finished!")
    print("Next step: Download llama-server.exe from:")
    print("https://github.com/ggerganov/llama.cpp/releases")
    print("and place it in 'runtime/llama/llama-server.exe' or project root.")
    print("=" * 60)

if __name__ == "__main__":
    main()
