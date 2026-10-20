# 🌌 RealmPlay (Standalone Edition)

> **Next-Generation Local AI Roleplay Engine with Proactive State Tracking, Multimodal Voice & Visual Pipelines.**  
> *Zero Authentication Required — Instant Single-User Local Play.*

RealmPlay is a privacy-first, locally-hosted roleplay platform engineered for deep immersion, long-term narrative continuity, and zero cloud dependency. Built on top of `llama.cpp` (`llama-server`), RealmPlay maintains persistent memories, real-time wardrobe states, mind-map lore routing, multimodal voice (Edge-TTS / RVC), and image synthesis (ComfyUI).

---

## ✨ Key Features

- **🎮 Standalone & Zero-Auth:** Launch the server and start roleplaying immediately — no registration, passwords, or databases required.
- **🧠 Autonomous State & Memory Engine:** Tracks dynamic narrative updates (`status`, `scenario`, `memory`, and `emotion`) via internal blocks, cleanly hidden from dialogue view.
- **👗 Dynamic Wardrobe & Appearance:** Tracks layered attire slots in real time; clothing states reactively adapt and feed directly into image generation prompts.
- **🗺️ Mind-Map Context Routing:** Dynamically injects only relevant lore nodes and memories to preserve your token budget.
- **🛡️ Anti-Echoing & Boundary Guardrails:** Prevents repetitive phrasing, conversational looping, and user godmoding with built-in delimiter auto-repair.
- **🎙️ Multimodal Voice & RVC:** Low-latency neural TTS (Thai & English) with optional local RVC voice conversion.
- **🎨 ComfyUI Visual Integration:** One-click image generation that seamlessly combines scene action, character appearance, current emotion, and active attire.
- **🎛️ Precision Sampling Controls:** Web GUI controls for Temperature, Min-P, Top-P, Top-K, DRY penalty, Repeat Last N, and DynaTemp.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- [llama.cpp](https://github.com/ggerganov/llama.cpp) binary or `llama-server.exe`
- (Optional) [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for image generation

### 2. Installation
```bash
git clone https://github.com/Zarchiki/RealmPlay.git
cd RealmPlay
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Models Setup
You can download models automatically using the included script:
```bash
python download_models.py
```
Or manually download the recommended GGUF model and Vision Projector:

| Type | Recommended Model | File Name | Hugging Face Source |
| :--- | :--- | :--- | :--- |
| **LLM (Text)** | Qwen3.5-4B Uncensored (Aggressive) | `Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` | [HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive) |
| **Vision (mmproj)** | Qwen3.5-4B Vision Projector | `mmproj-Qwen3.5-4B-mmproj-BF16.gguf` | [HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive) |

Place the downloaded files into:
- LLM text model: `models/text/` (or `models/`)
- Vision mmproj: `models/vision/` (or `models/`)
- `llama-server.exe` (from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases)): place in `runtime/llama/` or project root folder.

### 4. Configuration
Copy `config.example.json` to `config.json` (auto-created on first run if omitted):
```bash
# Windows:
copy config.example.json config.json
# Linux/macOS:
cp config.example.json config.json
```

### 5. Running RealmPlay
```bash
python server.py
# Or on Windows using launcher script:
start_realmplay.bat
```
Open your browser and go to `http://localhost:8000` to start chatting!

---

## 🙏 Acknowledgements & Credits

RealmPlay Standalone is built possible thanks to the amazing open-source AI community and projects:

- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** (by Georgi Gerganov & contributors) — High-performance LLM inference engine powering local roleplay.
- **[Qwen Team (Alibaba Cloud)](https://github.com/QwenLM/Qwen)** — Creators of the exceptional Qwen family of multilingual and multimodal models.
- **[HauhauCS](https://huggingface.co/HauhauCS)** — Creator of the uncensored and aggressive finetunes for Qwen3.5 that enable unrestrained creative roleplay.
- **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** (by comfyanonymous) — Modular and extensible diffusion GUI used for visual scene generation and sprites.
- **[Edge-TTS](https://github.com/rany2/edge-tts)** (by rany2) — Free, high-quality neural text-to-speech engine.
- **[Retrieval-based Voice Conversion (RVC)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)** — Cutting-edge voice timbre and pitch cloning architecture.
- **[FastAPI](https://github.com/fastapi/fastapi)** & **[Uvicorn](https://github.com/encode/uvicorn)** — Modern, fast asynchronous web server framework.
- **[Character Card V2 Spec](https://github.com/malfoys/character-card-spec-v2)** — Open standard for portable AI character card interchange.

---

## 📄 License & Terms of Use
Licensed under the **PolyForm Noncommercial License 1.0.0** (Free for personal use, no commercial use). See [LICENSE](LICENSE) for details.
