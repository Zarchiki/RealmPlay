"""Configuration and character/workflow editing endpoints."""
import asyncio
import io
import json
import logging
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image
from comfy_workflows import validate_workflow
from card_v2 import normalize_card, merge_card_data, read_legacy_card
import auth
import sampling
from observability import DEFAULT_RULE_SETTINGS, RULES

lock = threading.RLock()
FIELDS = ['name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example',
          'creatorcomment', 'avatar', 'talkativeness', 'fav', 'tags']
CHAT_STYLE_DEFAULTS = {
    'base': ('#e8eaf2', 14, False, False),
    'time': ('#e5e9f0', 12, True, False),
    'narration': ('#c4cad5', 14, False, True),
    'speaker': ('#eee9ff', 14, True, False),
    'speech': ('#ffffff', 14, True, False),
    'action': ('#bcc5d5', 14, False, True),
    'info': ('#e7e7e7', 12, False, False),
    'scenario': ('#e7e7e7', 12, False, False),
    'ooc': ('#b7bed5', 12, False, False),
    'code': ('#e7e7e7', 12, False, False),
}

PROFILE_IMAGE_PROTOCOL = {
    'version': 1,
    'aspect_ratio': '2:3',
    'width': 640,
    'height': 960,
    'workflow_targets': {
        'main': '9.wildcard_text',
        'negative': '10.wildcard_text',
        'emotion': '33.wildcard_text',
        'suffix': '39.wildcard_text',
    },
}


def _profile_main_prompt(kind, manual_prompt, subject_name=''):
    subject = 'character' if kind == 'character' else 'person'
    subject_label = subject_name.strip() if isinstance(subject_name, str) and subject_name.strip() else f'one {subject}'
    return ', '.join(part for part in (
        f'profile portrait of {subject_label}',
        'solo, vertical 2:3 composition, centered subject, upper body, looking at viewer',
        'clean readable silhouette, portrait photography composition, simple complementary background',
        manual_prompt.strip(),
    ) if part)


def _active_wardrobe_prompt(outfits):
    """Collect selected wardrobe tags without forcing Naked when no outfit was selected."""
    if not isinstance(outfits, dict):
        return ''
    tags = []
    for key, value in outfits.items():
        if isinstance(value, dict) and value.get('active') and str(value.get('prompt', '')).strip():
            tags.append(str(value['prompt']).strip())
        elif isinstance(value, str) and value.strip() and key not in ('current_outfit', 'outfits'):
            tags.append(value.strip())
    return ', '.join(dict.fromkeys(tags))


def chat_style_defaults():
    return {'layout': 'bubbles', 'font': 'system', 'styles': {
        key: {'color': color, 'size': size, 'bold': bold, 'italic': italic}
        for key, (color, size, bold, italic) in CHAT_STYLE_DEFAULTS.items()}}


def validate_chat_style(body):
    if not isinstance(body, dict) or set(body) - {'layout', 'font', 'styles'}:
        raise ValueError('Invalid chat settings')
    result = chat_style_defaults()
    layout = body.get('layout', result['layout'])
    if layout not in ('bubbles', 'clean', 'story'):
        raise ValueError('Invalid chat layout')
    result['layout'] = layout
    font = body.get('font', result['font'])
    if font not in ('system', 'serif', 'monospace'):
        raise ValueError('Invalid chat font')
    result['font'] = font
    styles = body.get('styles', {})
    if not isinstance(styles, dict) or set(styles) - set(CHAT_STYLE_DEFAULTS):
        raise ValueError('Invalid chat style category')
    for key, values in styles.items():
        if not isinstance(values, dict) or set(values) - {'color', 'size', 'bold', 'italic'}:
            raise ValueError(f'Invalid {key} style')
        style = result['styles'][key]
        style.update(values)
        if not isinstance(style['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', style['color']):
            raise ValueError(f'Invalid {key} color')
        if isinstance(style['size'], bool) or not isinstance(style['size'], int) or not 10 <= style['size'] <= 32:
            raise ValueError(f'Invalid {key} text size')
        if not isinstance(style['bold'], bool) or not isinstance(style['italic'], bool):
            raise ValueError(f'Invalid {key} text emphasis')
    return result


def config():
    return json.loads(Path('config.json').read_text(encoding='utf-8'))


def save_config(cfg):
    path = Path('config.json')
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def card_document(name, cards):
    baseline = cards.get_character_baseline(name)
    if not baseline:
        raise HTTPException(404, 'Character not found')
    path = Path('characters') / name / 'card.json'
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not old:
        try: old = cards.parse_png_card(str(path.parent / 'avatar.png'))
        except (ValueError, OSError): pass
    old = read_legacy_card(old or {'name': name})
    defaults = dict(name=name, description=baseline['persona'], personality=baseline['personality'],
                    scenario=baseline['scenario'], first_mes=baseline['first_mes'], mes_example='',
                    creatorcomment='', avatar='none', talkativeness=0.5, fav=False, tags=[])
    defaults.update(old)
    defaults.update(description=baseline['persona'], personality=baseline['personality'],
                    scenario=baseline['scenario'], first_mes=baseline['first_mes'])
    ordered = {k: defaults[k] for k in FIELDS}
    defaults = normalize_card({**defaults, **ordered})
    return {**ordered, 'spec': 'chara_card_v2', 'spec_version': '2.0', 'data': defaults}


def install(app, current_user, cards, engine, safe_name):
    def chat_settings_path(user):
        return Path('users') / safe_name(user) / 'settings.json'

    def _session_paths(user, char_name):
        root = Path("users") / safe_name(user) / safe_name(char_name)
        directory = root / "chat_sessions"
        return root, directory, directory / "index.json"

    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

    def _ensure_sessions(user, char_name):
        root, directory, index_path = _session_paths(user, char_name)
        state = cards.get_user_character_state(user, safe_name(char_name))
        with lock:
            if index_path.is_file():
                index = json.loads(index_path.read_text(encoding="utf-8"))
            else:
                session_id = uuid.uuid4().hex
                now = _now()
                payload = {"id": session_id, "title": "แชทเดิม", "created_at": now, "updated_at": now,
                           "history": state.get("history", []), "memory": state.get("memory", "")}
                _write_json(directory / f"{session_id}.json", payload)
                index = {"active_id": session_id, "sessions": [{
                    "id": session_id, "title": payload["title"], "created_at": now,
                    "updated_at": now, "message_count": len(payload["history"])
                }]}
                _write_json(index_path, index)
        return index

    def _sync_active_session(user, char_name, index=None):
        index = index or _ensure_sessions(user, char_name)
        active_id = index.get("active_id")
        if not active_id:
            return index
        state = cards.get_user_character_state(user, safe_name(char_name))
        _, directory, index_path = _session_paths(user, char_name)
        path = directory / f"{active_id}.json"
        old = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        now = _now()
        payload = {**old, "id": active_id, "title": old.get("title", "Chat"),
                   "created_at": old.get("created_at", now), "updated_at": now,
                   "history": state.get("history", []), "memory": state.get("memory", "")}
        with lock:
            _write_json(path, payload)
            for item in index.get("sessions", []):
                if item.get("id") == active_id:
                    item.update(title=payload["title"], updated_at=now,
                                message_count=len(payload["history"]))
            _write_json(index_path, index)
        return index

    @app.get("/api/characters/{char_name}/chat-sessions")
    def list_chat_sessions(char_name: str, user=Depends(current_user)):
        index = _sync_active_session(user, char_name)
        return index

    @app.post("/api/characters/{char_name}/chat-sessions")
    def create_chat_session(char_name: str, body: dict, user=Depends(current_user)):
        index = _sync_active_session(user, char_name)
        state = cards.get_user_character_state(user, safe_name(char_name))
        session_id = uuid.uuid4().hex
        now = _now()
        title = str(body.get("title") or f"Chat {len(index.get('sessions', [])) + 1}").strip()[:80]
        memory_mode = body.get("memory_mode", "copy")
        if memory_mode not in ("copy", "blank"):
            raise HTTPException(422, "memory_mode must be copy or blank")
        memory = state.get("memory", "") if memory_mode == "copy" else ""
        first = state.get("baseline", {}).get("first_mes", "")
        greeting_index = body.get('greeting_index', -1)
        greetings = state.get('baseline', {}).get('card_data', {}).get('alternate_greetings', [])
        if isinstance(greeting_index, bool) or not isinstance(greeting_index, int) or greeting_index < -1 or greeting_index >= len(greetings):
            raise HTTPException(422, 'Invalid alternate greeting index')
        if greeting_index >= 0:
            first = greetings[greeting_index]
        profile = auth.get_user_profile(user)
        first = first.replace('{{char}}', state['baseline'].get('card_data', {}).get('name', char_name)).replace('{{user}}', profile.get('display_name') or user)
        history = [{"role": "assistant", "content": first, "is_first_message": True}] if first else []
        payload = {"id": session_id, "title": title, "created_at": now, "updated_at": now,
                   "history": history, "memory": memory}
        _, directory, index_path = _session_paths(user, char_name)
        index.setdefault("sessions", []).insert(0, {
            "id": session_id, "title": title, "created_at": now, "updated_at": now,
            "message_count": len(history)
        })
        index["active_id"] = session_id
        with lock:
            _write_json(directory / f"{session_id}.json", payload)
            _write_json(index_path, index)
            cards.save_user_character_state(user, safe_name(char_name), {"history": history, "memory": memory})
        return {"ok": True, **index, "history": history, "memory": memory}

    @app.post("/api/characters/{char_name}/chat-sessions/{session_id}/activate")
    def activate_chat_session(char_name: str, session_id: str, user=Depends(current_user)):
        index = _sync_active_session(user, char_name)
        if not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise HTTPException(404, "Session not found")
        _, directory, index_path = _session_paths(user, char_name)
        path = directory / f"{session_id}.json"
        if not path.is_file():
            raise HTTPException(404, "Session not found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        index["active_id"] = session_id
        with lock:
            _write_json(index_path, index)
            cards.save_user_character_state(user, safe_name(char_name), {
                "history": payload.get("history", []), "memory": payload.get("memory", "")
            })
        return {"ok": True, "history": payload.get("history", []),
                "memory": payload.get("memory", ""), "active_id": session_id}

    @app.delete("/api/characters/{char_name}/chat-sessions/{session_id}")
    def delete_chat_session(char_name: str, session_id: str, user=Depends(current_user)):
        index = _sync_active_session(user, char_name)
        if session_id == index.get("active_id"):
            raise HTTPException(409, "ไม่สามารถลบแชทที่กำลังใช้งาน")
        _, directory, index_path = _session_paths(user, char_name)
        path = directory / f"{session_id}.json"
        index["sessions"] = [s for s in index.get("sessions", []) if s.get("id") != session_id]
        with lock:
            if path.is_file():
                path.unlink()
            _write_json(index_path, index)
        return {"ok": True, **index}


    @app.get('/api/chat-display-settings/defaults')
    def get_chat_display_defaults(user=Depends(current_user)):
        return chat_style_defaults()

    @app.get('/api/chat-display-settings')
    def get_chat_display_settings(user=Depends(current_user)):
        path = chat_settings_path(user)
        if not path.is_file():
            return chat_style_defaults()
        try:
            stored = json.loads(path.read_text(encoding='utf-8')).get('chat_display', {})
            return validate_chat_style(stored)
        except (OSError, ValueError, TypeError, AttributeError):
            logging.exception('Invalid chat display settings for %s', user)
            return chat_style_defaults()

    @app.post('/api/chat-display-settings')
    def put_chat_display_settings(body: dict, user=Depends(current_user)):
        try:
            settings = validate_chat_style(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with lock:
            path = chat_settings_path(user)
            path.parent.mkdir(parents=True, exist_ok=True)
            existing = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
            existing['chat_display'] = settings
            temp = path.with_suffix('.json.tmp')
            temp.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, path)
        return settings

    @app.get('/api/llm/sampling')
    def read_sampling(user=Depends(current_user)):
        settings = config().get('llm', {})
        return {'saved': sampling.saved(settings), 'effective': sampling.effective(settings), 'defaults': sampling.defaults()}

    @app.post('/api/llm/sampling/apply')
    def apply_sampling(body: dict, user=Depends(current_user)):
        try:
            values = sampling.validate(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        sampling.apply(values)
        return {'effective': sampling.effective(config().get('llm', {}))}

    @app.post('/api/llm/sampling/save')
    def save_sampling(body: dict, user=Depends(current_user)):
        try:
            values = sampling.validate(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with lock:
            cfg = config()
            cfg.setdefault('llm', {}).update(values)
            save_config(cfg)
            sampling.apply({})
        return {'saved': sampling.saved(cfg['llm']), 'effective': sampling.effective(cfg['llm']),
                'defaults': sampling.defaults()}

    @app.post('/api/llm/sampling/reset')
    def reset_sampling(user=Depends(current_user)):
        with lock:
            cfg = config()
            cfg.setdefault('llm', {}).update(sampling.defaults())
            save_config(cfg)
            sampling.apply({})
        return {'saved': sampling.saved(cfg['llm']), 'effective': sampling.effective(cfg['llm']),
                'defaults': sampling.defaults()}

    def image_path(user, kind):
        if kind not in ('profile', 'avatar'):
            raise HTTPException(404, 'Unknown image type')
        return Path('users') / safe_name(user) / ('profile_image.png' if kind == 'profile' else 'avatar.png')

    def bubble_root(user):
        root = Path('users') / safe_name(user) / 'chat_bubble_display'
        root.mkdir(parents=True, exist_ok=True)
        return root

    def bubble_settings_path(user):
        return bubble_root(user) / 'settings.json'

    def bubble_settings(user):
        defaults = {'user': {'scale': 1.0, 'x': 0, 'y': 0}, 'characters': {}}
        path = bubble_settings_path(user)
        try:
            saved = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        except (OSError, ValueError):
            saved = {}
        # Migrate the original 0..100 crop coordinates (50 was centered) to
        # the current -100..100 coordinates (0 is centered) once.
        if isinstance(saved, dict) and saved.get('display_coordinate_version') != 2:
            def migrate(values):
                if not isinstance(values, dict):
                    return values
                result = dict(values)
                for axis in ('x', 'y'):
                    value = result.get(axis)
                    if isinstance(value, (int, float)) and 0 <= float(value) <= 100:
                        result[axis] = round(float(value) - 50, 2)
                return result
            saved['user'] = migrate(saved.get('user'))
            if isinstance(saved.get('characters'), dict):
                saved['characters'] = {name: migrate(values) for name, values in saved['characters'].items()}
        defaults['user'].update(saved.get('user', {}) if isinstance(saved.get('user'), dict) else {})
        defaults['characters'] = saved.get('characters', {}) if isinstance(saved.get('characters'), dict) else {}
        return defaults

    def bubble_image_path(user, subject, name=None):
        root = bubble_root(user)
        if subject == 'user':
            return root / 'user.png'
        if subject == 'character' and name:
            card_document(safe_name(name), cards)
            return root / 'characters' / f'{safe_name(name)}.png'
        raise HTTPException(404, 'Unknown bubble image target')

    def save_user_image(path, raw):
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(413, 'Image is too large')
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.width * source.height > 24_000_000:
                    raise HTTPException(413, 'Image dimensions are too large')
                image = source.convert('RGBA')
                image.thumbnail((2048, 2048))
                image.save(temp, format='PNG')
            os.replace(temp, path)
        except HTTPException:
            raise
        except (OSError, ValueError) as exc:
            raise HTTPException(422, 'Invalid image') from exc
        finally:
            temp.unlink(missing_ok=True)

    @app.get('/api/chat-display/settings')
    def get_chat_display_settings(character_name: str = '', user=Depends(current_user)):
        settings = bubble_settings(user)
        character = safe_name(character_name) if character_name else ''
        return {
            'user': settings['user'],
            'character': settings['characters'].get(character, {'scale': 1.0, 'x': 0, 'y': 0}),
        }

    @app.post('/api/chat-display/settings')
    def set_chat_display_settings(body: dict, user=Depends(current_user)):
        target = body.get('target')
        if target not in ('user', 'character'):
            raise HTTPException(422, 'Invalid display target')
        character = safe_name(str(body.get('character_name', ''))) if target == 'character' else ''
        values = {key: body.get(key) for key in ('scale', 'x', 'y')}
        if (not isinstance(values['scale'], (int, float)) or not 1 <= float(values['scale']) <= 3 or
                any(not isinstance(values[key], (int, float)) or not -100 <= float(values[key]) <= 100 for key in ('x', 'y'))):
            raise HTTPException(422, 'Invalid display crop settings')
        settings = bubble_settings(user)
        target_settings = {key: round(float(value), 2) for key, value in values.items()}
        if target == 'user':
            settings['user'] = target_settings
        else:
            settings['characters'][character] = target_settings
        settings['display_coordinate_version'] = 2
        bubble_settings_path(user).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'ok': True, target: target_settings}

    @app.get('/api/chat-display/user/image')
    def get_user_bubble_image(user=Depends(current_user)):
        path = bubble_image_path(user, 'user')
        if not path.is_file(): raise HTTPException(404, 'Bubble image not found')
        return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})

    @app.post('/api/chat-display/user/image')
    async def put_user_bubble_image(file: UploadFile = File(...), user=Depends(current_user)):
        save_user_image(bubble_image_path(user, 'user'), await file.read(20 * 1024 * 1024 + 1))
        return {'ok': True}

    @app.delete('/api/chat-display/user/image')
    def delete_user_bubble_image(user=Depends(current_user)):
        bubble_image_path(user, 'user').unlink(missing_ok=True)
        return {'ok': True}

    @app.get('/api/chat-display/characters/{name}/image')
    def get_character_bubble_image(name: str, user=Depends(current_user)):
        path = bubble_image_path(user, 'character', name)
        if not path.is_file(): raise HTTPException(404, 'Bubble image not found')
        return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})

    @app.post('/api/chat-display/characters/{name}/image')
    async def put_character_bubble_image(name: str, file: UploadFile = File(...), user=Depends(current_user)):
        save_user_image(bubble_image_path(user, 'character', name), await file.read(20 * 1024 * 1024 + 1))
        return {'ok': True}

    @app.delete('/api/chat-display/characters/{name}/image')
    def delete_character_bubble_image(name: str, user=Depends(current_user)):
        bubble_image_path(user, 'character', name).unlink(missing_ok=True)
        return {'ok': True}

    @app.get('/api/auth/images/{kind}')
    def get_user_image(kind: str, user=Depends(current_user)):
        path = image_path(user, kind)
        if not path.is_file():
            raise HTTPException(404, 'Image not found')
        return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})

    @app.post('/api/auth/images/{kind}')
    async def put_user_image(kind: str, file: UploadFile = File(...), user=Depends(current_user)):
        path = image_path(user, kind)
        save_user_image(path, await file.read(20 * 1024 * 1024 + 1))
        return {'ok': True}

    @app.delete('/api/auth/images/{kind}')
    def delete_user_image(kind: str, user=Depends(current_user)):
        path = image_path(user, kind)
        path.unlink(missing_ok=True)
        return {'ok': True}

    @app.get('/api/image/profile-protocol')
    def get_profile_image_protocol(user=Depends(current_user)):
        return PROFILE_IMAGE_PROTOCOL

    @app.post('/api/auth/profile-image/generate')
    async def generate_profile_image(body: dict, user=Depends(current_user)):
        import comfy_client
        positive = body.get('positive', '')
        negative = body.get('negative', '')
        if not isinstance(positive, str) or not positive.strip() or len(positive) > 4000 or not isinstance(negative, str) or len(negative) > 4000:
            raise HTTPException(422, 'Enter a valid Positive and Negative prompt')
        try:
            profile = auth.get_user_profile(user)
            context = {
                'appearance': profile.get('persona', '').strip(),
                'wardrobe': '',
                'situation': '',
                'memory': '',
                'emotion': 'neutral expression',
            }
            main_prompt = _profile_main_prompt('user', positive, profile.get('display_name', ''))
            result = await comfy_client.generate_character_image(
                main_prompt,
                negative.strip(),
                context=context,
                width=PROFILE_IMAGE_PROTOCOL['width'],
                height=PROFILE_IMAGE_PROTOCOL['height'],
            )
            source = Path(result).resolve()
            if not source.is_relative_to(Path(comfy_client.OUTPUT_DIR).resolve()):
                raise ValueError('Invalid generated image path')
            save_user_image(image_path(user, 'profile'), source.read_bytes())
        except HTTPException:
            raise
        except Exception as exc:
            logging.exception('Profile image generation failed')
            raise HTTPException(502, f'Image generation failed: {exc}') from exc
        return {'ok': True, 'image_url': '/api/auth/images/profile', 'protocol': PROFILE_IMAGE_PROTOCOL}

    def character_profile_path(user, name):
        name = safe_name(name)
        card_document(name, cards)
        path = Path('users') / safe_name(user) / name / 'profile_image.png'
        # Preserve an older shared portrait once for each player, then keep
        # the portrait independent just like appearance and wardrobe state.
        legacy = Path('characters') / name / 'profile_image.png'
        if not path.exists() and legacy.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(legacy, path)
        return path

    @app.get('/api/characters/{name}/profile-image')
    def get_character_profile_image(name: str, user=Depends(current_user)):
        path = character_profile_path(user, name)
        if not path.is_file():
            raise HTTPException(404, 'Image not found')
        return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})

    @app.post('/api/characters/{name}/profile-image')
    async def put_character_profile_image(name: str, file: UploadFile = File(...), user=Depends(current_user)):
        save_user_image(character_profile_path(user, name), await file.read(20 * 1024 * 1024 + 1))
        return {'ok': True}

    @app.delete('/api/characters/{name}/profile-image')
    def delete_character_profile_image(name: str, user=Depends(current_user)):
        character_profile_path(user, name).unlink(missing_ok=True)
        return {'ok': True}

    @app.post('/api/characters/{name}/profile-image/generate')
    async def generate_character_profile_image(name: str, body: dict, user=Depends(current_user)):
        import comfy_client
        destination = character_profile_path(user, name)
        positive, negative = body.get('positive', ''), body.get('negative', '')
        if not isinstance(positive, str) or not positive.strip() or len(positive) > 4000 or not isinstance(negative, str) or len(negative) > 4000:
            raise HTTPException(422, 'Enter a valid Positive and Negative prompt')
        try:
            state = cards.get_user_character_state(user, safe_name(name))
            baseline = state.get('baseline', {})
            context = {
                'appearance': str(state.get('appearance', '')).strip(),
                'wardrobe': _active_wardrobe_prompt(state.get('outfits', {})),
                'situation': '',
                'memory': '',
                'emotion': str(state.get('emotion') or 'neutral expression').strip(),
            }
            main_prompt = _profile_main_prompt('character', positive, str(baseline.get('name') or name))
            result = await comfy_client.generate_character_image(
                main_prompt,
                negative.strip(),
                context=context,
                width=PROFILE_IMAGE_PROTOCOL['width'],
                height=PROFILE_IMAGE_PROTOCOL['height'],
            )
            source = Path(result).resolve()
            if not source.is_relative_to(Path(comfy_client.OUTPUT_DIR).resolve()):
                raise ValueError('Invalid generated image path')
            save_user_image(destination, source.read_bytes())
        except HTTPException:
            raise
        except Exception as exc:
            logging.exception('Character profile image generation failed')
            raise HTTPException(502, f'Image generation failed: {exc}') from exc
        return {
            'ok': True,
            'image_url': f'/api/characters/{name}/profile-image',
            'protocol': PROFILE_IMAGE_PROTOCOL,
        }

    @app.get('/api/configuration')
    def read_configuration(user=Depends(current_user)):
        cfg = config()
        return {**{k: cfg.get(k, {}) for k in ('llm', 'comfy')},
                'rules': {**DEFAULT_RULE_SETTINGS, **cfg.get('rules', {})},
                'proactive': cfg.get('proactive', {}),
                'rule_overrides': cfg.get('rule_overrides', {})}

    @app.post('/api/configuration')
    def write_configuration(body: dict, user=Depends(current_user)):
        with lock:
            cfg = config()
            for section, allowed in {
                'llm': {'model','mmproj','auto_load','context','gpu_layers','threads','batch_size','cache_type_k','cache_type_v','temperature','top_p','top_k','top_a','repetition_penalty','max_tokens'},
                'comfy': {'enabled','address','workflow','mappings','placeholders','sources','negative_prompt','prompt_suffix','emotion','emotion_prompts','checkpoint','vae','clip','sampler','scheduler','width','height','steps','cfg','seed','denoise','clip_skip','timeout','presets'},
                'rules': {'proactive_state','proactive_auto_reply','image_trigger','auto_wardrobe','loop_guard','prohibitions','expressive_vocalization','nsfw_mode','trace_prompts'},
                'proactive': {'enabled','min_interval_seconds','max_interval_seconds','max_consecutive','presence_ttl_seconds'},
                'rule_overrides': set(DEFAULT_RULE_SETTINGS) | set(RULES)
            }.items():
                values = body.get(section, {})
                if not isinstance(values, dict) or set(values) - allowed:
                    raise HTTPException(422, f'Invalid {section} configuration')
                cfg.setdefault(section, {}).update(values)
            if section == 'rule_overrides':
                if any(not isinstance(v, str) or len(v) > 2000 for v in values.values()):
                    raise HTTPException(422, 'Rule overrides must be text up to 2000 characters')
            limits = {'temperature':(0,5), 'top_p':(0,1),'top_a':(0,1),'top_k':(0,100000),'context':(512,131072),'threads':(1,128),'batch_size':(1,8192),'gpu_layers':(-1,1000),'max_tokens':(1,131072),'repetition_penalty':(0,3)}
            for key,(lo,hi) in limits.items():
                value = cfg['llm'].get(key)
                if value is not None and (not isinstance(value,(int,float)) or not lo <= value <= hi):
                    raise HTTPException(422, f'Invalid {key}')
            for key in ('cache_type_k', 'cache_type_v'):
                value = cfg['llm'].get(key)
                if value is not None and value not in {'q4_0', 'q8_0', 'f16'}:
                    raise HTTPException(422, f'Invalid {key}')
            # Top-K is a count; do not silently pretend fractional values work.
            if float(cfg['llm'].get('top_k',40)) % 1:
                raise HTTPException(422, 'Top-K must be an integer')
            if not isinstance(cfg['llm'].get('auto_load', False), bool):
                raise HTTPException(422, 'auto_load must be boolean')
            rules = {**DEFAULT_RULE_SETTINGS, **cfg.get('rules', {})}
            if any(not isinstance(rules[key], bool) for key in ('proactive_state','proactive_auto_reply','image_trigger','auto_wardrobe','loop_guard','prohibitions','expressive_vocalization','trace_prompts')):
                raise HTTPException(422, 'Rule toggles must be boolean')
            if rules['nsfw_mode'] not in ('local', 'fade_to_black', 'block'):
                raise HTTPException(422, 'Invalid NSFW policy mode')
            rules['proactive_state'] = True
            cfg['rules'] = rules
            proactive = cfg.setdefault('proactive', {})
            if not isinstance(proactive.get('enabled', True), bool):
                raise HTTPException(422, 'Proactive enabled must be boolean')
            for key, bounds in {
                'min_interval_seconds': (30, 86400),
                'max_interval_seconds': (30, 86400),
                'max_consecutive': (1, 20),
                'presence_ttl_seconds': (30, 3600),
            }.items():
                value = proactive.get(key)
                if value is not None and (not isinstance(value, int) or not bounds[0] <= value <= bounds[1]):
                    raise HTTPException(422, f'Invalid proactive {key}')
            if proactive.get('max_interval_seconds', 360) < proactive.get('min_interval_seconds', 180):
                raise HTTPException(422, 'Maximum proactive delay must be greater than or equal to minimum delay')
            comfy = cfg['comfy']
            if not isinstance(comfy.get('enabled', True), bool):
                raise HTTPException(422, 'ComfyUI custom workflow enabled must be boolean')
            # rgthree Seed (used by the bundled custom workflow) accepts at
            # most 2^50.  Keep UI/API validation aligned with the workflow.
            for key, limits in {'width':(64,8192),'height':(64,8192),'steps':(1,200),'cfg':(0,100),'denoise':(0,1),'timeout':(15,1800),'seed':(-1,2**50),'clip_skip':(0,24)}.items():
                value=comfy.get(key)
                if value is not None and (not isinstance(value,(float,int)) or not limits[0]<=value<=limits[1]):
                    raise HTTPException(422,f'Invalid ComfyUI {key}')
                if value is not None and key not in ('cfg','denoise','timeout') and float(value)%1:
                    raise HTTPException(422,f'{key} must be an integer')
            for key in ('mappings','placeholders','emotion_prompts','presets'):
                if key in comfy and not isinstance(comfy.get(key,{}),dict): raise HTTPException(422,f'{key} must be an object')
            if not all(isinstance(v,list) and all(isinstance(t,str) and '.' in t for t in v) for v in comfy.get('mappings',{}).values()):
                raise HTTPException(422,'Mappings must contain lists of node.input targets')
            sources=comfy.get('sources',[])
            if not isinstance(sources,list) or any(k not in ('appearance','wardrobe','situation','memory','emotion') for k in sources):
                raise HTTPException(422,'Invalid prompt sources')
            save_config(cfg)
        return {'ok': True}

    @app.on_event('startup')
    async def autoload():
        # Sampling values saved through the UI are the authoritative values
        # after a restart. Fill missing advanced keys once and discard any
        # transient Apply-only override left in the current Python process.
        with lock:
            cfg = config()
            opts = cfg.setdefault('llm', {})
            persisted_sampling = sampling.saved(opts)
            if any(opts.get(key) != value for key, value in persisted_sampling.items()):
                opts.update(persisted_sampling)
                save_config(cfg)
            sampling.apply({})
        if opts.get('auto_load') and opts.get('model'):
            try:
                await asyncio.to_thread(engine.start, model_name=opts['model'], mmproj=opts.get('mmproj'),
                    **{k: opts[k] for k in ('context','gpu_layers','threads','batch_size') if k in opts})
            except Exception:
                logging.exception('Automatic model load failed')

    @app.get('/api/comfy/workflows')
    def workflows(user=Depends(current_user)):
        folder = Path('data/workflows'); folder.mkdir(parents=True, exist_ok=True)
        return sorted(p.name for p in folder.glob('*.json'))

    @app.get('/api/comfy/workflows/{name}')
    def read_workflow(name: str, user=Depends(current_user)):
        path = Path('data/workflows') / safe_name(name)
        if not path.is_file(): raise HTTPException(404, 'Workflow not found')
        return json.loads(path.read_text(encoding='utf-8'))

    @app.post('/api/comfy/workflows/{name}')
    def write_workflow(name: str, graph: dict, user=Depends(current_user)):
        try: validate_workflow(graph)
        except ValueError as exc: raise HTTPException(422, str(exc))
        name = safe_name(name)
        if not name.endswith('.json'): raise HTTPException(422, 'Use a .json filename')
        folder = Path('data/workflows'); folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'ok': True}

    @app.get('/api/comfy/presets')
    def get_workflow_presets(user=Depends(current_user)):
        cfg = config()
        comfy = cfg.get('comfy', {})
        presets = comfy.get('presets', {})
        # Built-in sensible default presets for common workflows
        defaults = {
            'Anima (CatPony UNET)': {
                'workflow': 'RealmPlayADV_Anima.json',
                'checkpoint': 'catpony_animaV10_fp16.safetensors',
                'vae': 'qwenImageVAE.safetensors',
                'clip': 'qwen_3_06b_base.safetensors',
                'sampler': 'euler_ancestral',
                'scheduler': 'normal',
                'width': 512,
                'height': 768,
                'steps': 20,
                'cfg': 7.0,
                'clip_skip': 0,
                'denoise': 1.0,
                'mappings': {
                    'prompt': ['9.wildcard_text'],
                    'negative_prompt': ['10.wildcard_text'],
                    'emotion': ['33.wildcard_text'],
                    'suffix': ['39.wildcard_text'],
                    'denoise': ['11.denoise'],
                    'scheduler': ['11.scheduler'],
                    'cfg': ['11.cfg'],
                    'height': ['15.height'],
                    'width': ['15.width'],
                    'steps': ['11.steps'],
                    'sampler': ['11.sampler_name'],
                    'seed': ['11.seed']
                }
            },
            'Default (Pony Checkpoint)': {
                'workflow': 'RealmPlayADV_Default.json',
                'checkpoint': 'catpony_aniIlV90.safetensors',
                'vae': '(Automatic / Built-in)',
                'clip': '(Automatic / From Workflow)',
                'sampler': 'euler_ancestral',
                'scheduler': 'normal',
                'width': 512,
                'height': 768,
                'steps': 20,
                'cfg': 7.0,
                'clip_skip': 2,
                'denoise': 1.0,
                'mappings': {
                    'prompt': ['9.wildcard_text'],
                    'negative_prompt': ['10.wildcard_text'],
                    'emotion': ['33.wildcard_text'],
                    'suffix': ['39.wildcard_text'],
                    'denoise': ['11.denoise'],
                    'scheduler': ['11.scheduler'],
                    'cfg': ['11.cfg'],
                    'height': ['15.height'],
                    'width': ['15.width'],
                    'steps': ['11.steps'],
                    'sampler': ['11.sampler_name'],
                    'seed': ['11.seed'],
                    'checkpoint': ['46.ckpt_name']
                }
            }
        }
        # Merge user presets over defaults
        merged = {**defaults, **presets}
        return merged

    @app.post('/api/comfy/presets/{name}')
    def save_workflow_preset(name: str, preset_data: dict, user=Depends(current_user)):
        name = name.strip()[:60]
        if not name:
            raise HTTPException(422, 'Invalid preset name')
        with lock:
            cfg = config()
            comfy = cfg.setdefault('comfy', {})
            presets = comfy.setdefault('presets', {})
            presets[name] = preset_data
            save_config(cfg)
        return {'ok': True, 'presets': comfy.get('presets', {})}

    @app.delete('/api/comfy/presets/{name}')
    def delete_workflow_preset(name: str, user=Depends(current_user)):
        name = name.strip()
        with lock:
            cfg = config()
            comfy = cfg.setdefault('comfy', {})
            presets = comfy.setdefault('presets', {})
            if name in presets:
                del presets[name]
                save_config(cfg)
        return {'ok': True}

    @app.get('/api/comfy/path-test')
    async def comfy_path_test(workflow: str = '', user=Depends(current_user)):
        """Dry-run parameter routing without queueing an image generation job."""
        settings = config().get('comfy', {})
        filename = safe_name(workflow or settings.get('workflow', ''))
        path = Path('data/workflows') / filename
        if not filename or not path.is_file():
            raise HTTPException(404, 'Workflow not found')
        graph = json.loads(path.read_text(encoding='utf-8'))
        try:
            validate_workflow(graph)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

        # Edges point from a producer node to every consumer node.
        downstream = {str(node_id): set() for node_id in graph}
        for consumer_id, node in graph.items():
            for value in node.get('inputs', {}).values():
                if isinstance(value, list) and len(value) == 2 and str(value[0]) in graph:
                    downstream[str(value[0])].add(str(consumer_id))
        output_nodes = {str(node_id) for node_id, node in graph.items()
                        if node.get('class_type') in ('SaveImage', 'PreviewImage')}

        def reaches_output(start):
            queue, seen = [(str(start), [str(start)])], set()
            while queue:
                current, route = queue.pop(0)
                if current in seen:
                    continue
                seen.add(current)
                if current in output_nodes:
                    return route
                queue.extend((nxt, route + [nxt]) for nxt in downstream.get(current, ()))
            return []

        def placeholder_targets(parameter):
            token = '%' + parameter + '%'
            found = []
            for node_id, node in graph.items():
                for key, value in node.get('inputs', {}).items():
                    if isinstance(value, str) and token in value:
                        found.append((str(node_id), key, 'placeholder'))
            return found

        aliases = {'checkpoint': ('checkpoint', 'model'), 'sampler': ('sampler',),
                   'scheduler': ('scheduler',), 'cfg': ('cfg', 'scale')}
        mappings = settings.get('mappings', {})
        checks = []
        for parameter, names in aliases.items():
            targets = []
            for source in names:
                for target in mappings.get(source, []):
                    try:
                        node_id, field = str(target).split('.', 1)
                    except ValueError:
                        continue
                    targets.append((node_id, field, 'mapping'))
                targets.extend(placeholder_targets(source))
            unique, result = set(), []
            for node_id, field, method in targets:
                marker = (node_id, field)
                if marker in unique:
                    continue
                unique.add(marker)
                node = graph.get(node_id)
                if not node or field not in node.get('inputs', {}):
                    result.append({'node_id': node_id, 'input': field, 'method': method,
                                   'valid': False, 'error': 'Target does not exist'})
                    continue
                current = node['inputs'][field]
                route = reaches_output(node_id)
                result.append({'node_id': node_id, 'node_type': node.get('class_type'),
                               'title': node.get('_meta', {}).get('title', ''), 'input': field,
                               'method': method, 'current': current,
                               'configured': settings.get(parameter, ''), 'valid': True,
                               'reaches_output': bool(route), 'route': route})
            checks.append({'parameter': parameter, 'configured': settings.get(parameter, ''),
                           'connected': any(item.get('valid') for item in result),
                           'reaches_output': any(item.get('reaches_output') for item in result),
                           'targets': result})

        # Verify that node class names are known to the connected ComfyUI instance.
        comfy_online, unknown_types, comfy_error = False, [], None
        try:
            import comfy_client
            info = await asyncio.to_thread(comfy_client.request_json, '/object_info',
                                           settings.get('address', comfy_client.DEFAULT_COMFY_URL))
            comfy_online = True
            unknown_types = sorted({node.get('class_type') for node in graph.values()
                                    if node.get('class_type') not in info})
        except Exception as exc:
            comfy_error = str(exc)
        return {'workflow': filename, 'checks': checks, 'output_nodes': sorted(output_nodes),
                'comfy_online': comfy_online, 'unknown_node_types': unknown_types,
                'comfy_error': comfy_error, 'queued': False}

    @app.get('/api/comfy/options')
    async def comfy_options(user=Depends(current_user)):
        import comfy_client
        try:
            info = await asyncio.to_thread(comfy_client.request_json, '/object_info', config().get('comfy',{}).get('address',comfy_client.DEFAULT_COMFY_URL))
            def choices(node, key):
                value = info.get(node,{}).get('input',{}).get('required',{}).get(key,[[]])[0]
                return value if isinstance(value,list) else []
            # Merge standard checkpoints (CheckpointLoaderSimple) and diffusion UNETs (UNETLoader)
            ckpt_choices = choices('CheckpointLoaderSimple', 'ckpt_name')
            unet_choices = choices('UNETLoader', 'unet_name')
            all_models = sorted(set(ckpt_choices + unet_choices))
            raw_vaes = choices('VAELoader', 'vae_name')
            # Prepend Automatic / Built-in option so users can rely on checkpoint's embedded VAE
            vae_options = ['(Automatic / Built-in)'] + [v for v in raw_vaes if v != '(Automatic / Built-in)']
            # CLIP choices from CLIPLoader
            raw_clips = choices('CLIPLoader', 'clip_name')
            clip_options = ['(Automatic / From Workflow)'] + [c for c in raw_clips if c != '(Automatic / From Workflow)']
            return {'checkpoint': all_models, 'vae': vae_options, 'clip': clip_options,
                    'sampler': choices('KSampler', 'sampler_name'), 'scheduler': choices('KSampler', 'scheduler')}
        except Exception as exc: raise HTTPException(502, str(exc))

    @app.get('/api/characters/{name}/card-document')
    def get_card(name: str, user=Depends(current_user)):
        name = safe_name(name)
        document = card_document(name, cards)
        summary = cards.get_character_baseline(name).get('char_summary', '')
        def estimate(value):
            return len(re.findall(r'[\u0E00-\u0E7F]|[A-Za-z0-9_]+|[^\s]', str(value or '')))
        # Count each narrative field once, excluding duplicated V2 wrappers and image metadata.
        keys = ('name', 'description', 'personality', 'scenario', 'first_mes',
                'mes_example', 'creatorcomment', 'creator_notes', 'system_prompt',
                'post_history_instructions', 'alternate_greetings', 'character_book')
        parts = []
        for key in keys:
            value = document['data'].get(key, '')
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False) if value else ''
            count = estimate(value)
            if count:
                parts.append({'field': key, 'tokens': count})
        total = sum(part['tokens'] for part in parts)
        for part in parts:
            part['percent'] = round(100 * part['tokens'] / total, 1) if total else 0
        document['analysis'] = {'summary_markdown': summary, 'summary_tokens': estimate(summary),
                                'total_tokens': total, 'parts': parts, 'estimated': True,
                                'scope': 'Character Card text; excludes image data and duplicate V2 fields'}
        return document

    @app.get('/api/characters/{name}/summary')
    def get_character_summary(name: str, user=Depends(current_user)):
        """Return the saved chat summary without rebuilding it from the card."""
        name = safe_name(name)
        baseline = cards.get_character_baseline(name)
        if baseline is None:
            raise HTTPException(404, 'Character not found')
        return {'name': name, 'summary': baseline.get('char_summary', '')}

    @app.put('/api/characters/{name}/summary')
    def put_character_summary(name: str, body: dict, user=Depends(current_user)):
        """Save a manually edited Char_Summary.md for the selected character."""
        name = safe_name(name)
        card_document(name, cards)  # validates that this character exists
        summary = body.get('summary')
        if not isinstance(summary, str):
            raise HTTPException(422, 'Summary must be text')
        if len(summary) > 100_000:
            raise HTTPException(422, 'Summary is too long')
        (Path('characters') / name / 'Char_Summary.md').write_text(summary, encoding='utf-8')
        return {'name': name, 'summary': summary}

    @app.post('/api/characters/{name}/card-document')
    def put_card(name: str, body: dict, user=Depends(current_user)):
        name = safe_name(name)
        previous = card_document(name, cards)
        data = body.get('data', body)
        if not isinstance(data,dict): raise HTTPException(422,'Invalid card data')
        data = merge_card_data(previous['data'], data)
        if data.get('character_book', 'absent') is None:
            data.pop('character_book')
        try:
            data = normalize_card(data)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        if data.get('name') != previous['data']['name']:
            raise HTTPException(422, 'Renaming a character is not supported in this editor')
        for key in FIELDS[:8]:
            if not isinstance(data.get(key),str): raise HTTPException(422,f'{key} must be text')
        if not isinstance(data.get('tags'),list) or not all(isinstance(t,str) for t in data['tags']): raise HTTPException(422,'Invalid tags')
        if not isinstance(data.get('fav'),bool) or not isinstance(data.get('talkativeness'),(int,float)) or not 0 <= data['talkativeness'] <= 1: raise HTTPException(422,'Invalid card options')
        cards.update_character_baseline(name, dict(persona=data['description'], **{k:data[k] for k in ('personality','scenario','first_mes')}))
        (Path('characters') / name / 'card.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        return card_document(name,cards)

    @app.post('/api/characters/{name}/avatar')
    async def avatar(name: str, file: UploadFile = File(...), user=Depends(current_user)):
        name = safe_name(name); card_document(name,cards)
        raw = await file.read(20 * 1024 * 1024 + 1)
        if len(raw) > 20 * 1024 * 1024: raise HTTPException(413,'Image is too large')
        try:
            with Image.open(io.BytesIO(raw)) as img:
                img.convert('RGBA').save(Path('characters') / name / 'avatar.png','PNG')
        except Exception: raise HTTPException(422,'Invalid image')
        return {'ok': True}
