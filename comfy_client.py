"""ComfyUI workflows with typed placeholders and bounded asynchronous I/O."""
import asyncio
import json
import secrets
import time
import uuid
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error
import re
from comfy_workflows import build_default_workflow, compile_workflow, extract_character_eye_tags
from logic_set_engine import OrderedTagSet

DEFAULT_COMFY_URL = 'http://127.0.0.1:8188'
OUTPUT_DIR = 'generated_images'
DEFAULT_CONTEXT_SOURCES = ('location', 'appearance', 'wardrobe', 'situation', 'memory', 'emotion')
# rgthree Seed accepts an INT in [-2^50, 2^50]. Keep RealmPlay's global seed
# inside that intersection so one custom workflow cannot reject an otherwise
# valid KSampler seed.
SEED_MAX = 2**50

# Reused from Aurelia's emotion resolver. The keys form RealmPlay's public
# Emotion catalog. Values are visual directions for the dedicated EMOTION
# workflow slot, not text shown in chat.
DEFAULT_EMOTION_PROMPTS = {
    'neutral': 'neutral expression, calm face, relaxed eyes, natural gaze',
    'happy': 'soft happy expression, gentle smile, relaxed eyes, warm gaze, natural blush',
    'pleased': 'soft happy expression, gentle smile, relaxed eyes, warm gaze, natural blush',
    'gentle': 'soft happy expression, gentle smile, relaxed eyes, warm gaze, natural blush',
    'calm': 'neutral expression, calm face, relaxed eyes, natural gaze',
    'sad': 'crying expression, tears, wet eyes, trembling lips, sober blush',
    'crying': 'crying expression, tears, wet eyes, trembling lips, subdued blush',
    'angry': 'angry expression, furrowed brows, intense glare, tense jaw',
    'shocked': 'surprisingly shocked, wide open eyes, saliva drooling, sober blush, gasping',
    'terrified': 'unpleasant expression, terrified, crying, tear, saliva drooling, hurting, sober blush, wide eyes, trembling',
    'panicked': 'unpleasant expression, terrified, crying, tear, saliva drooling, hurting, sober blush, wide eyes, trembling',
    'victim': 'unpleasant expression, terrified, crying, tear, saliva drooling, hurting, sober blush, wide eyes, trembling',
    'broken': 'crying deeply, heavy tears, saliva drooling, hurting, despair expression, empty eyes, sober blush, sobbing',
    'despair': 'crying deeply, heavy tears, saliva drooling, hurting, despair expression, empty eyes, sober blush, sobbing',
    'submissive': 'embarrassing expression, submissive, sober blush, tear, looking away, shy',
    'humiliated': 'embarrassing expression, submissive, sober blush, tear, looking away, shy',
    'shy_excited': 'shy excited expression, warm blush, bright eyes, hesitant smile',
    'aroused': 'moaning, open mouth, saliva drooling, heavy blush, arousing, half-closed eyes',
    'lust': 'moaning, open mouth, saliva drooling, heavy blush, arousing, half-closed eyes',
    'moaning': 'moaning, open mouth, saliva drooling, heavy blush, arousing, half-closed eyes',
    'ahegao': 'hysteria, exciting, tongue out, rolled up eyes, saliva drooling, ahegao, heavy blush',
    'hysteria': 'hysteria, exciting, tongue out, rolled up eyes, saliva drooling, ahegao, heavy blush',
    'crazy': 'hysteria, exciting, tongue out, rolled up eyes, saliva drooling, ahegao, heavy blush',
    'dominant': 'pleasant, joyous, arousing, fierce, sadistic smile, confident expression, dominant stare',
    'femdom': 'pleasant, joyous, arousing, fierce, sadistic smile, confident expression, dominant stare',
    'sadistic': 'pleasant, joyous, arousing, fierce, sadistic smile, confident expression, dominant stare',
    'fainting': 'fainting, closed eyes, pale face, limp expression',
    'unconscious': 'unconscious, fainting, closed eyes, saliva drooling, pale face, limp',
    'mindbreak': 'blank stare, empty eyes, emotionless expression',
    # Adult emotion/face states. These belong in the EMOTION wildcard only;
    # they never add an action, character identity, or wardrobe to POSITIVE.
    'seductive': 'seductive expression, sultry gaze, parted lips, confident blush',
    'flirty': 'playful flirtatious smile, warm blush, inviting gaze',
    'teasing': 'mischievous teasing smile, half-lidded eyes, faint blush',
    'yearning': 'yearning expression, longing gaze, soft blush, parted lips',
    'needy': 'needy expression, pleading eyes, heavy blush, parted lips',
    'begging': 'pleading expression, watery eyes, deep blush, parted lips',
    'breathless': 'breathless expression, open mouth, flushed cheeks, half-closed eyes',
    'orgasmic': 'intense pleasure expression, heavy blush, half-closed eyes, open mouth',
    'euphoric': 'euphoric pleasure expression, blissful smile, heavy blush, closed eyes',
    'afterglow': 'relaxed afterglow expression, warm flush, soft smile, sleepy eyes',
    'lewd': 'lewd expression, heavy blush, half-lidded eyes, parted lips',
    'shameless': 'shameless confident expression, direct gaze, playful smile, warm blush',
    'overwhelmed': 'overwhelmed expression, teary eyes, heavy blush, trembling lips',
    'desperate': 'desperate expression, pleading eyes, heavy blush, open mouth',
    'embarrassed_aroused': 'embarrassed aroused expression, looking away, intense blush, half-closed eyes',
    'hopeful': 'hopeful expression, gentle optimistic smile, sparkling eyes, warm gaze, slight blush',
}
DEFAULT_EMOTION_CATEGORIES = {
    'general': ('neutral', 'happy', 'pleased', 'gentle', 'calm', 'hopeful', 'sad', 'crying', 'angry', 'shocked'),
    'distress': ('terrified', 'panicked', 'victim', 'broken', 'despair', 'fainting', 'unconscious', 'mindbreak'),
    'power_and_submission': ('submissive', 'humiliated', 'dominant', 'femdom', 'sadistic'),
    'intimate_nsfw': ('aroused', 'lust', 'moaning', 'ahegao', 'hysteria', 'crazy', 'seductive', 'flirty', 'teasing', 'yearning', 'needy', 'begging', 'breathless', 'orgasmic', 'euphoric', 'afterglow', 'lewd', 'shameless', 'overwhelmed', 'desperate', 'embarrassed_aroused'),
}
EMOTION_ALIASES = {
    'smile': 'happy', 'smiling': 'happy', 'joy': 'happy', 'joyful': 'happy',
    'hope': 'hopeful', 'optimistic': 'hopeful', 'expectant': 'hopeful',
    'tearful': 'crying', 'tears': 'crying', 'fear': 'terrified', 'scared': 'terrified', 'fearful': 'terrified',
    'surprised': 'shocked', 'shock': 'shocked', 'embarrassed': 'submissive', 'shy': 'submissive',
    'lustful': 'lust', 'horny': 'lust', 'arousal': 'aroused', 'orgasm': 'orgasmic',
    'flirtatious': 'flirty', 'desire': 'yearning', 'dominance': 'dominant', 'dom': 'dominant',
}

_CONFLICTING_EYE_COLOR_RE = re.compile(
    r"\b(?:red|blue|green|brown|amber|hazel|yellow|golden|gold|purple|violet|pink|crimson|black|dark|grey|gray|silver|white|orange|aqua|cyan|turquoise|emerald|ruby|sapphire|heterochromia)\s+eyes\b",
    re.IGNORECASE,
)


def _inject_appearance_eye_color(emotion_prompt, appearance=None):
    """Ensure the emotion prompt sent to FaceDetailer carries the character's eye color from Appearance."""
    base = str(emotion_prompt or '').strip()
    eye_tags = extract_character_eye_tags(appearance) if appearance else []
    if not eye_tags:
        return base
    # If the emotion describes closed eyes (e.g. sleeping, fainting, closed eyes), don't force open eye color tags
    if re.search(r"\bclosed\s+eyes\b", base, re.IGNORECASE):
        return base
    parts = [p.strip() for p in base.split(',') if p.strip()]
    eye_lower_set = {t.casefold() for t in eye_tags}
    filtered_parts = []
    for p in parts:
        pl = p.casefold()
        if pl in eye_lower_set:
            continue
        # Remove any hardcoded eye color in the emotion preset that conflicts with character appearance
        if _CONFLICTING_EYE_COLOR_RE.search(p) and pl not in eye_lower_set:
            p = _CONFLICTING_EYE_COLOR_RE.sub("", p).strip(" ,")
            if not p:
                continue
        filtered_parts.append(p)
    # Insert character eye color right after the first expression tag via OrderedTagSet Union
    insert_pos = 1 if filtered_parts else 0
    merged_set = OrderedTagSet(filtered_parts[:insert_pos]).union(eye_tags, filtered_parts[insert_pos:])
    return merged_set.to_prompt()


def resolve_emotion_prompt(emotion, custom=None, appearance=None):
    raw = str(emotion or 'neutral').strip().lower()
    # Strip intensity or cause if passed as a composite string (e.g. "hopeful (65%), cause: ...")
    raw = raw.split('(')[0].split(',')[0].strip()
    key = raw.replace('-', '_').replace(' ', '_')
    key = EMOTION_ALIASES.get(key, key)
    custom = custom if isinstance(custom, dict) else {}
    normalized = {str(k).strip().lower().replace('-', '_').replace(' ', '_'): str(v).strip()
                  for k, v in custom.items() if str(v).strip()}
    
    # 1. Direct match in configured custom or default catalog
    if key in normalized:
        return _inject_appearance_eye_color(normalized[key], appearance)
    if key in DEFAULT_EMOTION_PROMPTS:
        return _inject_appearance_eye_color(DEFAULT_EMOTION_PROMPTS[key], appearance)
    
    # 2. Check parts if composite emotion (e.g., eager_anticipation -> anticipation -> excited / happy)
    parts = key.split('_')
    for part in parts:
        alias_part = EMOTION_ALIASES.get(part, part)
        if alias_part in normalized:
            return _inject_appearance_eye_color(normalized[alias_part], appearance)
        if alias_part in DEFAULT_EMOTION_PROMPTS:
            return _inject_appearance_eye_color(DEFAULT_EMOTION_PROMPTS[alias_part], appearance)

    # 3. Known fallbacks for anticipation/eager/devotion
    if any(p in key for p in ('anticipat', 'eager', 'expect')):
        res = normalized.get('excited') or DEFAULT_EMOTION_PROMPTS.get('excited') or 'excited expression, bright wide eyes, eager smile'
        return _inject_appearance_eye_color(res, appearance)
    if 'devot' in key or 'seren' in key:
        res = normalized.get('gentle') or DEFAULT_EMOTION_PROMPTS.get('gentle') or 'soft happy expression, gentle smile, relaxed eyes, warm gaze, natural blush'
        return _inject_appearance_eye_color(res, appearance)
    if 'resist' in key or 'conflict' in key:
        res = normalized.get('uneasy') or DEFAULT_EMOTION_PROMPTS.get('uneasy') or 'uneasy expression, cautious eyes, tense brow, restrained breath'
        return _inject_appearance_eye_color(res, appearance)

    # 4. Fallback: return descriptive prompt instead of bare unrendered keyword
    return _inject_appearance_eye_color(f"{raw.replace('_', ' ')} expression, detailed face, expressive eyes", appearance)

def request_json(path, address, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(address.rstrip('/') + path, data=data, headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        try:
            detail = json.loads(raw)
            node_errors = detail.get('node_errors', {}) if isinstance(detail, dict) else {}
            messages = []
            for node_id, node_error in node_errors.items():
                for error in node_error.get('errors', []):
                    messages.append(f"node {node_id}: {error.get('details') or error.get('message')}")
            summary = '; '.join(messages) or detail.get('error', {}).get('message') or raw
        except (ValueError, AttributeError):
            summary = raw or str(exc)
        raise ValueError(f'ComfyUI HTTP {exc.code}: {summary}') from exc

def queue_prompt(graph, server_address=DEFAULT_COMFY_URL):
    result = request_json('/prompt',server_address,{'prompt':graph})
    if not result.get('prompt_id') or result.get('node_errors'): raise ValueError(f'Workflow rejected: {result}')
    return result['prompt_id']

def get_history(prompt_id, server_address=DEFAULT_COMFY_URL):
    return request_json('/history/' + prompt_id,server_address)

def resolve_checkpoint(settings, address):
    configured = str(settings.get('checkpoint') or '').strip()
    if configured:
        return configured
    # Preserve compatibility by reading the checkpoint or UNET model from the selected custom graph.
    filename = settings.get('workflow', '')
    path = Path('data/workflows') / Path(filename).name if filename else None
    if path and path.is_file():
        try:
            graph = json.loads(path.read_text(encoding='utf-8'))
            for node in graph.values():
                ctype = node.get('class_type')
                if ctype == 'CheckpointLoaderSimple':
                    value = node.get('inputs', {}).get('ckpt_name')
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                elif ctype == 'UNETLoader':
                    value = node.get('inputs', {}).get('unet_name')
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except (OSError, ValueError, TypeError):
            pass
    # Last fallback: use the first checkpoint or UNET reported by ComfyUI.
    info = request_json('/object_info', address)
    ckpt_choices = info.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
    if isinstance(ckpt_choices, list) and ckpt_choices:
        return str(ckpt_choices[0])
    unet_choices = info.get('UNETLoader', {}).get('input', {}).get('required', {}).get('unet_name', [[]])[0]
    if isinstance(unet_choices, list) and unet_choices:
        return str(unet_choices[0])
    raise ValueError('No checkpoint or UNET is available. Select one in ComfyUI Image Gen settings')


def apply_generation_seed(graph, seed):
    """Give every unlinked seed input a valid generation seed.

    Custom workflows often contain rgthree Seed nodes, detailers and wildcard
    processors in addition to the primary KSampler.  A `-1` sentinel is useful
    in RealmPlay settings, but it is not valid input for rgthree.  Linked inputs
    are preserved because their upstream node owns their value.
    """
    seed = int(seed)
    for node in graph.values():
        inputs = node.get('inputs', {})
        for field, current in list(inputs.items()):
            normalized = str(field).casefold().replace('_', '')
            if normalized not in {'seed', 'seedvalue', 'noiseseed'}:
                continue
            if isinstance(current, bool) or isinstance(current, (list, dict)):
                continue
            if isinstance(current, (int, float)):
                inputs[field] = seed
    return graph


def preferred_image_outputs(history_entry, compiled_graph):
    """Yield final saved images before previews/intermediate node output.

    ComfyUI history contains output from many preview nodes.  Dictionary order
    is not a workflow guarantee, so selecting its first image can return the
    pre-detailer image.  Save nodes with an `images` input are terminal output
    nodes and therefore take precedence.
    """
    outputs = (history_entry or {}).get('outputs', {})
    preferred_ids = [
        str(node_id) for node_id, node in compiled_graph.items()
        if 'save' in str(node.get('class_type', '')).casefold()
        and 'images' in node.get('inputs', {})
    ]
    inspected = set()
    for node_id in preferred_ids + list(outputs.keys()):
        node_id = str(node_id)
        if node_id in inspected:
            continue
        inspected.add(node_id)
        for image in outputs.get(node_id, {}).get('images', []):
            yield image

def build_positive_prompt_parts(base_prompt, context=None, sources=None):
    """Compose the exact POSITIVE wildcard text ensuring Location prefix and Action Seed take priority."""
    context = context or {}
    enabled = set(sources or DEFAULT_CONTEXT_SOURCES)
    parts = []

    h_mode_active = bool(context.get("h_mode_active") or context.get("h_mode"))
    # `naked` is a state tag, not a garment.  Keep it immediately after the
    # H-Mode NSFW prefix so the visual model sees the exposure state before
    # action, appearance, or any remaining active accessories.
    wardrobe_val = str(context.get("wardrobe") or "").strip()
    wardrobe_tags = [tag.strip() for tag in wardrobe_val.split(",") if tag.strip()]
    naked_active = any(tag.casefold() == "naked" for tag in wardrobe_tags)
    wardrobe_without_naked = ", ".join(
        tag for tag in wardrobe_tags if tag.casefold() != "naked"
    )
    if h_mode_active:
        parts.append("POV, NSFW")
        if "wardrobe" in enabled and naked_active:
            parts.append("naked")

    if context.get("precomposed_positive"):
        action_seed = str(base_prompt or "").strip()
        if action_seed:
            parts.append(action_seed)
        return list(dict.fromkeys(part for part in parts if part))

    # 0. Location Prefix (Always prefix location earliest before all other positive prompt elements)
    loc_val = str(context.get("location") or "").strip()
    if loc_val:
        parts.append(loc_val)

    # 1. Action & Dynamic Posture (Priority #1: Placed immediately after location prefix)
    action_seed = str(base_prompt or "").strip()
    if action_seed:
        if loc_val and action_seed.lower().startswith(loc_val.lower()):
            trimmed_action = action_seed[len(loc_val):].lstrip(" ,.-").strip()
            if trimmed_action:
                parts.append(trimmed_action)
        else:
            parts.append(action_seed)

    # 2. Appearance (Subject Identity, Hair, Eyes)
    if "appearance" in enabled and context.get("appearance"):
        val = str(context["appearance"]).strip()
        if val:
            parts.append(val)

    # 3. Wardrobe (Clothing / Naked status)
    if "wardrobe" in enabled and wardrobe_val:
        # In H-Mode, naked was intentionally emitted next to NSFW above.
        # Keep all still-active accessories and other tags in their normal
        # wardrobe position without duplicating the exposure tag.
        val = wardrobe_without_naked if h_mode_active and naked_active else wardrobe_val
        if val:
            parts.append(val)

    # 4. Situation & Environment (Background, Atmosphere)
    if "situation" in enabled and context.get("situation"):
        val = str(context["situation"]).strip()
        if val:
            parts.append(val)

    # 5. Salient Memory cues
    if "memory" in enabled and context.get("memory"):
        val = str(context["memory"]).strip()
        if val:
            parts.append(val)

    # 6. Terminal Gesture / Posture (H-Mode exhaustion)
    if context.get("terminal_gesture"):
        val = str(context["terminal_gesture"]).strip()
        if val:
            parts.append(val)

    return list(dict.fromkeys(part for part in parts if part))


async def generate_character_image(positive_prompt, negative_prompt='', server_address=None,
        width=None, height=None, steps=None, cfg=None, sampler=None, context=None, progress=None, cancelled=None, timeout=None):
    settings = json.loads(Path('config.json').read_text(encoding='utf-8')).get('comfy',{})
    address = server_address or settings.get('address',DEFAULT_COMFY_URL)
    context = context or {}
    sources = settings.get('sources', list(DEFAULT_CONTEXT_SOURCES))
    parts = build_positive_prompt_parts(positive_prompt, context, sources)
    requested_seed = int(settings.get('seed', -1))
    # -1 means random. Fixed values are normalized for rgthree compatibility.
    seed = secrets.randbelow(SEED_MAX + 1) if requested_seed < 0 else requested_seed % (SEED_MAX + 1)
    values = dict(settings.get('placeholders',{}))
    requested_emotion = context.get('emotion') or settings.get('emotion', 'neutral')
    values.update(prompt=', '.join(parts), appearance=str(context.get('appearance') or '').strip(),
        negative_prompt=negative_prompt or settings.get('negative_prompt',''),
        suffix=settings.get('prompt_suffix',''), emotion=resolve_emotion_prompt(requested_emotion, settings.get('emotion_prompts'), appearance=context.get('appearance')) if 'emotion' in sources else '',
        width=width or settings.get('width',576), height=height or settings.get('height',1024),
        steps=steps or settings.get('steps',25), cfg=cfg if cfg is not None else settings.get('cfg',7),
        sampler=sampler or settings.get('sampler','euler'), scheduler=settings.get('scheduler','normal'),
        seed=seed, denoise=settings.get('denoise',1),
        model='', checkpoint='', vae=settings.get('vae',''), clip=settings.get('clip',''),
        sam_model=settings.get('sam_model', ''),
        clip_skip=-abs(int(settings.get('clip_skip',1))))
    values['checkpoint'] = await asyncio.to_thread(resolve_checkpoint, settings, address)
    values['model'] = values['checkpoint']
    values['scale'] = values['cfg']  # SillyTavern ComfyUI placeholder name.
    for key in ('width','height','steps'):
        if not isinstance(values[key],int) or values[key]<1: raise ValueError(f'Invalid {key}')
    if settings.get('enabled', True):
        filename = settings.get('workflow','')
        if not filename or Path(filename).name != filename:
            raise ValueError('Select an imported ComfyUI API workflow first')
        graph = json.loads((Path('data/workflows') / filename).read_text(encoding='utf-8'))
        compiled = compile_workflow(graph, values, settings.get('mappings',{}))
    else:
        compiled = build_default_workflow(values)
    compiled = apply_generation_seed(compiled, values['seed'])
    if progress:
        progress('ComfyUI: workflow compiled', 18, {'positive': values['prompt'], 'negative': values['negative_prompt'], 'context': context, 'seed': values['seed']})
    prompt_id = await asyncio.to_thread(queue_prompt,compiled,address)
    if progress:
        progress('ComfyUI: queued', 30, {'prompt_id': prompt_id})
    effective_timeout = float(timeout) if timeout is not None else float(settings.get('timeout', 300))
    deadline = time.monotonic()+max(15,min(1800,effective_timeout))
    while time.monotonic()<deadline:
        await asyncio.sleep(1)
        if cancelled and cancelled():
            # /interrupt stops only the currently executing ComfyUI job.  The caller
            # owns the run id, so the UI cannot interrupt a different user's trace.
            try:
                await asyncio.to_thread(request_json, '/interrupt', address, {})
            except Exception:
                pass
            raise asyncio.CancelledError('ComfyUI generation was cancelled')
        if progress:
            progress('ComfyUI: generating', 55)
        entry=(await asyncio.to_thread(get_history,prompt_id,address)).get(prompt_id)
        if not entry: continue
        if entry.get('status',{}).get('status_str')=='error': raise RuntimeError(f'ComfyUI execution failed: {entry.get("status")}')
        for img in preferred_image_outputs(entry, compiled):
            query=urllib.parse.urlencode({k:img.get(k,'output' if k=='type' else '') for k in ('filename','subfolder','type')})
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            dest=Path(OUTPUT_DIR)/(uuid.uuid4().hex+Path(img['filename']).suffix)
            def download():
                with urllib.request.urlopen(address.rstrip('/')+'/view?'+query,timeout=30) as response: dest.write_bytes(response.read())
            await asyncio.to_thread(download)
            if progress:
                progress('ComfyUI: final saved image ready', 95, {'output': str(dest)})
            return str(dest)
        if entry.get('status',{}).get('completed'): raise RuntimeError('Workflow completed without an image output')
    raise TimeoutError(f'ComfyUI prompt {prompt_id} timed out; check its queue before retrying')
