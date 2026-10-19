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

### 3. Configuration
Copy `config.example.json` to `config.json` and adjust your model and server settings:
```bash
# Windows:
copy config.example.json config.json
# Linux/macOS:
cp config.example.json config.json
```

### 4. Running RealmPlay
```bash
python server.py
# Or on Windows using batch script:
start_realmplay.bat
```
Open your browser and go to `http://localhost:8000` to start chatting!

---

## 📄 License & Terms of Use
Licensed under the **PolyForm Noncommercial License 1.0.0** (Free for personal use, no commercial use). See [LICENSE](LICENSE) for details.
