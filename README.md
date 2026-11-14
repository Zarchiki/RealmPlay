# 🌌 RealmPlay (Full Multi-User Edition)

> **Next-Generation Local AI Roleplay Platform with Multi-User Authentication, Proactive State Tracking, Multimodal Voice & Visual Pipelines.**

RealmPlay is a privacy-first, locally-hosted roleplay platform engineered for deep immersion, long-term narrative continuity, and multi-user isolation. Built on top of `llama.cpp` (`llama-server`), RealmPlay maintains persistent memories, real-time wardrobe states, mind-map lore routing, multimodal voice (Edge-TTS / RVC), and image synthesis (ComfyUI).

This repository is the **Full Multi-User Edition**: includes robust hashed-password authentication (PBKDF2-HMAC-SHA256), individual player profiles, isolated chat histories, and dedicated user storage spaces.

---

## ✨ Key Features

- **🔐 Multi-User Authentication & Isolation:** Secure password-protected login with isolated per-user workspaces (`users/<username>/`), personal chat sessions, and independent memories.
- **🧠 Autonomous State & Memory Engine:** Tracks dynamic narrative updates (`status`, `scenario`, `memory`, and `emotion`) via internal blocks, cleanly hidden from dialogue view.
- **👗 Dynamic Wardrobe & Appearance:** Tracks layered attire slots in real time; clothing states reactively adapt and feed directly into image generation prompts.
- **🗺️ Mind-Map Context Routing:** Dynamically injects only relevant lore nodes and memories to preserve your token budget.
- **🛡️ Anti-Echoing & Boundary Guardrails:** Prevents repetitive phrasing, conversational looping, and user godmoding with built-in delimiter auto-repair.
- **🎙️ Multimodal Voice & RVC:** Low-latency neural TTS (Thai & English) with optional local RVC voice conversion.
- **🎨 ComfyUI Visual Integration:** One-click image generation that seamlessly combines scene action, character appearance, current emotion, and active attire.
- **🎛️ Precision Sampling Controls:** Web GUI controls for Temperature, Min-P, Top-P, Top-K, DRY penalty, Repeat Last N, and DynaTemp.

---

## 🧩 Full Feature Map

### Accounts, access, and deployment

- Account registration, login, logout, profile editing, password reset, and single-login protection.
- Admin user management: create, remove, and reset user accounts.
- Per-user data isolation for every character, conversation, image, inventory, and state record.
- Local LAN operation plus optional Cloudflare tunnel controls for remote access.
- Built-in LLM engine controls: status, model discovery, start, stop, text-model selection, and vision-model support.

### Character library and authoring

- Character Card V2 import from PNG or JSON, export, editable cards, avatar management, and sprite support.
- Create a character manually or generate a randomized starter character with a portrait workflow.
- Shared Character Card data stays separate from each player's private relationship and story state.
- Character profile editor for scenario, permanent memory, status, image appearance, individual interaction profile, and wardrobe.
- Multiple alternate greetings and character chat sessions with create, activate, rename, archive, and restore behaviour.

### Chat and roleplay

- Streaming-style chat workflow with normal send, regenerate, continue, edit, delete one message, and delete message ranges.
- Marker-aware roleplay input: `*...*` is a completed physical action, quoted text is dialogue, and plain text is dialogue/request for the character to decide.
- Thai and English language adaptation, role-aware pronouns, dialogue/action formatting, TTS dialogue extraction, and delimiter repair.
- Recent-history budget control, context routing, loop protection, duplicate-response detection, and one corrective rewrite when needed.
- Character-led initiative, proactive presence/check-ins, relationship-aware responses, normal-scene progression, and H-Mode scene progression.
- H-Mode state tracks canonical stage, substage, position, location, character needs, H-Energy, arousal, exhaustion, aftercare, and restart decisions.
- CNC roleplay is an explicit session setting. It changes fictional scene preference only; the character remains the in-story decision maker and direct user stop/pause/end requests take priority.

### Current state and turn records

- `current_datablock` stores the live state used by the next turn and the current UI.
- `turn_records` store immutable per-message snapshots used for history display, image context, regenerate, and rollback.
- Status, scenario, memory, emotion, time, scene state, inventory, and wardrobe are synchronized as structured state rather than exposed in visible dialogue.
- Rollback and regeneration restore the selected turn record before producing a replacement response.
- SQLite provides a transactional runtime index; readable per-user files remain available as storage and recovery artifacts.

### Wardrobe, inventory, gifts, and progression

- Layered wardrobe slots for outerwear, tops, inner layers, bottoms, footwear, accessories, and naked state.
- Outfit grid, presets, catalog items, direct equip/unequip controls, wardrobe inventory, and character inventory bag.
- User actions and character actions can wear or remove an item by exact item name or supported clothing group.
- Character wardrobe requests may be accepted, refused, or clarified in character. Completed changes update live state and the matching turn record together.
- Auto Wardrobe can synchronize completed character clothing actions when enabled.
- Gift transfer, character acceptance, affection changes, player rewards, stats, skills, shop purchases, gacha, and usable items.

### Image generation and visual continuity

- ComfyUI image generation from natural-language requests, `/image`, or `[[image: ...]]` commands.
- Image context combines action seed, current location, image appearance, active outfit, emotion, selected memories, and configured prompt suffix.
- `active_sd_prompt` uses only active wardrobe slots; stored or removed items are excluded.
- A chat-bubble image uses the wardrobe and state record from its own turn, not a later outfit change.
- Image intent preview, editable prompt override, per-message regeneration, cancellation, gallery/history attachment, avatar/profile portrait generation, and workflow validation.

### Voice and audio

- Edge-TTS voices with Thai and English support, adjustable voice, speed, and pitch.
- Optional RVC conversion and configurable voice parameters.
- Dialogue-focused speech extraction, replay support, cached audio, and cache inspection/cleanup.

### Rules, observability, and quality controls

- Rule Inspector with configurable rule order, essential-rule protection, rule descriptions, and execution visibility.
- Runtime activity monitor for chat, image, and TTS: progress, cancellation, duration, errors, prompt traces, and resource snapshots.
- Per-user statistics for completed, failed, and cancelled work.
- Context and rule routers expose which state nodes and rule instructions were selected for a request.
- Configurable loop guard, output prohibitions, image trigger, automatic wardrobe, proactive state, expressive vocalization, and local-model content policy.
- Built-in feature audit checklist for backend, LLM, ComfyUI, TTS/RVC, rules, library, activity logs, desktop, and mobile checks.

### Interface and data management

- Responsive desktop/mobile interface with chat bubbles, clean/story layouts, configurable typography, side panels, profile cards, and character gallery.
- Player Status, character status, needs, emotion, current situation, permanent memories, wardrobe, inventory, rewards, and skills panels.
- Character images, generated images, audio cache, logs, durable state files, turn metadata, and active chat-session data are stored locally.

For state ownership and the exact current-state/turn-record lifecycle, see [RealmPlay State Protocol](docs/REALMPLAY-STATE-PROTOCOL.md). For runtime rules and monitoring, see [Rules and Observability](docs/RULES-AND-OBSERVABILITY.md).

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
Open your browser and navigate to `http://localhost:8000` to log in or register a new user account!

---

## 🙏 Acknowledgements & Credits

RealmPlay is built possible thanks to the amazing open-source AI community and projects:

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
