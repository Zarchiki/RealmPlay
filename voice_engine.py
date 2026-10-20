"""Voice Engine for RealmPlay supporting:
- Edge-TTS with Thai Neural Voices (th-TH-PremwadeeNeural, th-TH-NiwatNeural)
- Custom External API TTS
- RVC Voice Converter with Pitch Shift & Custom Options
- Audio caching system
"""
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import unicodedata
import uuid
from typing import Optional, Dict, Any

AUDIO_CACHE_DIR = "audio_output"
_SPEECH_LOCKS: Dict[str, asyncio.Lock] = {}

def ensure_audio_dir():
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

def extract_dialogue(text: str) -> str:
    """Extract only spoken dialogue enclosed in quotation marks.
    Supports: "...", “...”, 「...」, 『...』
    Excludes inner thoughts (...), actions *...*, and notes [...].
    """
    import re
    if not text:
        return ""
    # Pattern to match quotes
    pattern = r'["“「『]([^"”」』]+)["”」』]'
    dialogues = re.findall(pattern, text)
    if dialogues:
        cleaned_dialogues = []
        for d in dialogues:
            # Strip any accidental nested asterisks *action* or thoughts (...) inside quotes
            clean_d = re.sub(r'\*[^*]*\*', '', d)
            clean_d = re.sub(r'\([^)]*\)', '', clean_d)
            clean_d = re.sub(r'\[[^\]]*\]', '', clean_d).strip()
            if clean_d:
                cleaned_dialogues.append(clean_d)
        if cleaned_dialogues:
            cleaned = " ".join(cleaned_dialogues)
            return sanitize_speech_text(cleaned)

    # Remove any code blocks (e.g. ```scenario/info ... ```)
    cleaned = re.sub(r'```[\s\S]*?```', '', text)
    # Fallback: remove asterisks actions *action*, inner thoughts (thought), and brackets [note]
    cleaned = re.sub(r'\*[^*]*\*', '', cleaned)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned).strip()
    return sanitize_speech_text(cleaned if cleaned else text)


def sanitize_speech_text(text: str, max_chars: int = 1800) -> str:
    """Normalize roleplay output into text accepted reliably by speech providers."""
    import re
    value = unicodedata.normalize("NFKC", text or "")
    value = re.sub(r'!\[image\]', ' ', value, flags=re.I)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', ' ', value)
    # Control and formatting code points occasionally arrive from copied roleplay text.
    value = ''.join(' ' if unicodedata.category(char) in ('Cc', 'Cf', 'Cs') else char for char in value)
    value = re.sub(r'\s+', ' ', value).strip()
    if len(value) > max_chars:
        cutoff = value.rfind(' ', 0, max_chars)
        value = value[:cutoff if cutoff > max_chars // 2 else max_chars].rstrip() + '…'
    return value


def get_cache_filename(text: str, voice: str, pitch: int, rvc_model: Optional[str] = None, rvc_index: Optional[str] = None, index_rate: Optional[float] = None, protect: Optional[float] = None, rate: str = "+0%") -> str:
    payload = f"{text}_{voice}_{pitch}_{rvc_model or 'none'}_{rvc_index or ''}_{index_rate}_{protect}_{rate}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{h}.wav" if rvc_model else f"{h}.mp3"

async def generate_edge_tts(text: str, voice: str = "th-TH-PremwadeeNeural", rate: str = "+0%", pitch_str: str = "+0Hz", output_path: str = None) -> str:
    """Generate speech using Edge TTS, retrying transient no-audio responses."""
    ensure_audio_dir()
    if not output_path:
        output_path = os.path.join(AUDIO_CACHE_DIR, f"edge_{hashlib.md5(text.encode()).hexdigest()[:10]}.mp3")
    if os.path.isfile(output_path):
        os.remove(output_path)
    
    # Microsoft occasionally returns an empty stream even for a valid voice.
    # Retry before declaring the provider unavailable.
    last_error = None
    try:
        import edge_tts
        for attempt in range(3):
            try:
                # edge-tts 7.x accepts its implicit neutral defaults, but some Edge
                # endpoints reject the same values when supplied explicitly.
                options = {}
                if rate and rate != "+0%":
                    options["rate"] = rate
                if pitch_str and pitch_str != "+0Hz":
                    options["pitch"] = pitch_str
                communicate = edge_tts.Communicate(text=text, voice=voice, **options)
                await communicate.save(output_path)
                if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                    return output_path
                raise RuntimeError("Edge-TTS produced an empty audio file")
            except Exception as exc:
                last_error = exc
                if os.path.exists(output_path):
                    os.remove(output_path)
                if attempt < 2:
                    await asyncio.sleep(attempt + 1)
    except ImportError as exc:
        last_error = exc

    # Keep the CLI as a final fallback and expose its actual diagnostic if it fails.
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", voice,
    ]
    if rate and rate != "+0%":
        cmd.extend(["--rate", rate])
    if pitch_str and pitch_str != "+0Hz":
        cmd.extend(["--pitch", pitch_str])
    cmd.extend(["--write-media", output_path])
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await proc.communicate()
    except asyncio.CancelledError:
        proc.terminate()
        await proc.wait()
        if os.path.exists(output_path):
            os.remove(output_path)
        raise
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
        return output_path
    details = stderr.decode("utf-8", "ignore").strip() or stdout.decode("utf-8", "ignore").strip()
    raise RuntimeError(
        "Edge-TTS did not return audio after three retries. "
        f"Check internet access or try again. {details or last_error or ''}".strip()
    )

def find_rvc_python() -> str:
    """Finds python executable that contains torch and rvc_python dependencies."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(app_dir, "runtime", "python.exe"),
        os.path.join(app_dir, "venv", "Scripts", "python.exe"),
        os.path.join(app_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(os.path.dirname(sys.executable), "python.exe"),
        sys.executable
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return sys.executable

def resolve_rvc_model_path(model_name_or_path: str) -> Optional[str]:
    """Resolves RVC model by checking exact path or RealmPlay models/voice directory."""
    if not model_name_or_path:
        return None
    if os.path.isfile(model_name_or_path):
        return os.path.abspath(model_name_or_path)
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(app_dir, "models", "voice"),
        os.path.join(app_dir, "model_dir", "voice")
    ]
    target_name = os.path.basename(model_name_or_path)
    for voice_dir in candidates:
        if os.path.isdir(voice_dir):
            direct = os.path.join(voice_dir, model_name_or_path)
            if os.path.isfile(direct):
                return os.path.abspath(direct)
            for root, _, files in os.walk(voice_dir):
                if target_name in files:
                    return os.path.abspath(os.path.join(root, target_name))
    return None

async def run_rvc_pitch_shift(
    input_audio: str,
    output_audio: str,
    model_path: str,
    pitch: int = 0,
    device: str = "cpu",
    index_path: Optional[str] = None,
    index_rate: Optional[float] = None,
    protect: Optional[float] = None
) -> str:
    """Invokes RVC inference with pitch shift and index/ratio settings."""
    ensure_audio_dir()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    local_worker = os.path.join(app_dir, "rvc_worker.py")
    if not os.path.exists(local_worker):
        raise FileNotFoundError("RVC worker script (rvc_worker.py) not found in RealmPlay")
    worker_script = local_worker

    worker_dir = os.path.dirname(os.path.abspath(worker_script))
    python_exe = find_rvc_python()

    cmd = [
        python_exe, os.path.abspath(worker_script),
        "--model", os.path.abspath(model_path),
        "--input", os.path.abspath(input_audio),
        "--output", os.path.abspath(output_audio),
        "--pitch", str(pitch),
        "--device", device
    ]
    if index_path:
        cmd.extend(["--index", index_path])
    if index_rate is not None:
        cmd.extend(["--index-rate", str(index_rate)])
    if protect is not None:
        cmd.extend(["--protect", str(protect)])

    print(f"[VoiceEngine] Running RVC: {python_exe} with model {model_path} (pitch: {pitch}, index: {index_path}, index_rate: {index_rate}, protect: {protect}) in {worker_dir}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=worker_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await proc.communicate()
    except asyncio.CancelledError:
        proc.terminate()
        await proc.wait()
        for path in (input_audio, output_audio):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        raise
    if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
        err_msg = stderr.decode('utf-8', 'ignore').strip() or stdout.decode('utf-8', 'ignore').strip()
        print(f"[VoiceEngine] RVC stderr: {err_msg}")
        raise RuntimeError(f"RVC conversion failed: {err_msg or 'output file not generated'}")
    return output_audio

async def synthesize_speech(
    text: str,
    voice: str = "th-TH-PremwadeeNeural",
    pitch: int = 0,
    rate: str = "+0%",
    rvc_model: Optional[str] = None,
    rvc_index: Optional[str] = None,
    index_rate: Optional[float] = None,
    protect: Optional[float] = None
) -> str:
    """Unified synthesis pipeline: TTS -> Optional RVC -> Return Audio Path."""
    ensure_audio_dir()
    text = sanitize_speech_text(text)
    if not text:
        raise ValueError("No speakable text was found in this message")

    resolved_model = resolve_rvc_model_path(rvc_model) if rvc_model else None
    cache_file = os.path.join(AUDIO_CACHE_DIR, get_cache_filename(text, voice, pitch, resolved_model, rvc_index, index_rate, protect, rate))
    lock = _SPEECH_LOCKS.setdefault(os.path.abspath(cache_file), asyncio.Lock())

    # Requests for the same bubble can overlap (for example test + play, or a double tap).
    # Serialize each cache key and give every attempt its own temporary filenames.
    async with lock:
        if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0:
            return cache_file
        if os.path.exists(cache_file):
            os.remove(cache_file)

        job_id = uuid.uuid4().hex[:10]
        tmp_base = os.path.join(AUDIO_CACHE_DIR, f"temp_{job_id}.mp3")
        tmp_converted = os.path.join(AUDIO_CACHE_DIR, f"rvc_{job_id}.wav")
        try:
            await generate_edge_tts(text=text, voice=voice, rate=rate, output_path=tmp_base)

            # Step 2: Apply RVC if requested and resolved.
            if resolved_model and os.path.exists(resolved_model):
                try:
                    await run_rvc_pitch_shift(
                        input_audio=tmp_base,
                        output_audio=tmp_converted,
                        model_path=resolved_model,
                        pitch=pitch,
                        index_path=rvc_index,
                        index_rate=index_rate,
                        protect=protect
                    )
                    os.replace(tmp_converted, cache_file)
                    return cache_file
                except Exception as rvc_err:
                    print(f"[VoiceEngine] RVC conversion error ({rvc_err}), falling back to base TTS.")

            # No RVC, or RVC fell back: cache valid MP3 with its own extension.
            base_cache = os.path.join(AUDIO_CACHE_DIR, get_cache_filename(text, voice, pitch, rate=rate))
            os.replace(tmp_base, base_cache)
            return base_cache
        finally:
            for temporary in (tmp_base, tmp_converted):
                if os.path.exists(temporary):
                    try:
                        os.remove(temporary)
                    except OSError:
                        pass

