"""Validated, live sampling settings for the built-in llama.cpp server."""
import json
import math
import re
import threading

SPECS = {
    'temperature': (0.7, 0, 5, float),
    'top_p': (0.9, 0, 1, float),
    'top_k': (40, 0, 100000, int),
    'top_a': (0.0, 0, 1, float),
    'min_p': (0.0, 0, 1, float),
    'typical_p': (1.0, 0, 1, float),
    'tfs_z': (1.0, 0, 1, float),
    'repetition_penalty': (1.1, 0, 3, float),
    'repeat_last_n': (64, 0, 131072, int),
    'presence_penalty': (0.0, -2, 2, float),
    'frequency_penalty': (0.0, -2, 2, float),
    'max_tokens': (1024, 1, 131072, int),
    'mirostat': (0, 0, 2, int),
    'mirostat_tau': (5.0, 0, 20, float),
    'mirostat_eta': (0.1, 0, 2, float),
    'dynatemp_range': (0.0, 0, 5, float),
    'dynatemp_exponent': (1.0, 0, 5, float),
    'xtc_probability': (0.0, 0, 1, float),
    'xtc_threshold': (0.1, 0, 1, float),
    'dry_multiplier': (0.0, 0, 10, float),
    'dry_base': (1.75, 0, 10, float),
    'dry_allowed_length': (2, 0, 1000, int),
}
RESERVED = {'messages', 'model', 'stream', 'prompt', 'tools', 'tool_choice', 'n', 'user'}
_lock = threading.RLock()
_override = {}


def defaults():
    return {key: spec[0] for key, spec in SPECS.items()} | {'extra': {}}


def validate(values):
    if not isinstance(values, dict) or set(values) - (set(SPECS) | {'extra'}):
        raise ValueError('Unknown sampling parameter')
    result = {}
    for key, value in values.items():
        if key == 'extra':
            if not isinstance(value, dict) or len(value) > 64 or len(json.dumps(value)) > 16384:
                raise ValueError('Custom parameters must be a small JSON object')
            if any(not isinstance(k, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,63}', k) or k in RESERVED for k in value):
                raise ValueError('Invalid custom parameter name')
            result[key] = value
            continue
        default, minimum, maximum, kind = SPECS[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f'Invalid {key}')
        if kind is int and int(value) != value:
            raise ValueError(f'{key} must be an integer')
        result[key] = kind(value)
    return result


def saved(settings):
    return defaults() | validate({key: settings[key] for key in set(SPECS) | {'extra'} if key in settings})


def effective(settings):
    with _lock:
        return saved(settings) | _override.copy()


def apply(values):
    validated = validate(values)
    with _lock:
        _override.clear()
        _override.update(validated)


def payload(settings, temperature=None, top_p=None, max_tokens=None):
    values = effective(settings)
    result = dict(values['extra'])
    result.update({
        'temperature': values['temperature'] if temperature is None else temperature,
        'top_p': values['top_p'] if top_p is None else top_p,
        'top_k': values['top_k'],
        'top_a': values['top_a'],
        'repeat_penalty': values['repetition_penalty'],
        'max_tokens': values['max_tokens'] if max_tokens is None else max_tokens,
    })
    optional = {'min_p':'min_p','typical_p':'typical_p','tfs_z':'tfs_z',
        'repeat_last_n':'repeat_last_n','presence_penalty':'presence_penalty',
        'frequency_penalty':'frequency_penalty','mirostat':'mirostat',
        'mirostat_tau':'mirostat_tau','mirostat_eta':'mirostat_eta',
        'dynatemp_range':'dynatemp_range','dynatemp_exponent':'dynatemp_exponent',
        'xtc_probability':'xtc_probability','xtc_threshold':'xtc_threshold',
        'dry_multiplier':'dry_multiplier','dry_base':'dry_base',
        'dry_allowed_length':'dry_allowed_length'}
    for key, wire_key in optional.items():
        if values[key] != SPECS[key][0]:
            result[wire_key] = values[key]
    return result
