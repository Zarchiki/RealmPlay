"""Lossless Tavern Character Card V2 validation and lorebook activation."""
from copy import deepcopy
import math
import re

TEXT_FIELDS = ('name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example',
               'creator_notes', 'system_prompt', 'post_history_instructions', 'creator', 'character_version')


def normalize_card(document):
    if not isinstance(document, dict):
        raise ValueError('Card must be a JSON object')
    if 'spec' in document:
        if document['spec'] != 'chara_card_v2' or document.get('spec_version') != '2.0':
            raise ValueError('Supported card format: chara_card_v2 / 2.0')
        data = deepcopy(document.get('data'))
    else:
        data = deepcopy(document)
    if not isinstance(data, dict):
        raise ValueError('data must be an object')
    for key in TEXT_FIELDS:
        data.setdefault(key, '')
        if not isinstance(data[key], str):
            raise ValueError(f'{key} must be text')
    if not data['name'].strip():
        raise ValueError('Character name is required')
    for key in ('tags', 'alternate_greetings'):
        data.setdefault(key, [])
        string_list(data[key], key)
    extensions(data, 'card')
    if 'character_book' in data:
        book = data['character_book']
        if not isinstance(book, dict):
            raise ValueError('character_book must be an object')
        extensions(book, 'character_book')
        for key in ('name', 'description'):
            optional(book, key, str)
        for key in ('scan_depth', 'token_budget'):
            number(book, key, minimum=0)
        optional(book, 'recursive_scanning', bool)
        book.setdefault('entries', [])
        if not isinstance(book['entries'], list):
            raise ValueError('character_book.entries must be an array')
        for entry in book['entries']:
            if not isinstance(entry, dict):
                raise ValueError('Each book entry must be an object')
            extensions(entry, 'entry')
            for key, default in (('keys', []), ('content', ''), ('enabled', True), ('insertion_order', 0)):
                entry.setdefault(key, default)
            string_list(entry['keys'], 'keys')
            if 'secondary_keys' in entry:
                string_list(entry['secondary_keys'], 'secondary_keys')
            for key in ('content', 'name', 'comment'):
                optional(entry, key, str)
            for key in ('enabled', 'case_sensitive', 'selective', 'constant'):
                optional(entry, key, bool)
            for key in ('insertion_order', 'priority', 'id'):
                number(entry, key)
            if 'position' in entry and entry['position'] not in ('before_char', 'after_char'):
                raise ValueError('Invalid entry position')
    return data


def extensions(obj, label):
    obj.setdefault('extensions', {})
    if not isinstance(obj['extensions'], dict):
        raise ValueError(f'{label}.extensions must be an object')


def string_list(value, label):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f'{label} must be an array of strings')


def optional(obj, key, kind):
    if key in obj and not isinstance(obj[key], kind):
        raise ValueError(f'{key} must be {kind.__name__}')


def number(obj, key, minimum=None):
    if key in obj:
        v = obj[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or (minimum is not None and v < minimum):
            raise ValueError(f'Invalid number: {key}')


def lorebook_context(book, history, latest, expand=lambda s: s):
    """Estimate tokens conservatively without requiring a model tokenizer."""
    if not book:
        return '', ''
    depth = int(book.get('scan_depth', 2))
    source = '\n'.join(str(m.get('content', '')) for m in (history[-depth:] if depth else []))
    source += '\n' + latest
    base_source = source
    entries = book.get('entries', [])
    selected = set()
    budget = int(book.get('token_budget', 2048))
    def cost(text):
        return len(text.encode('utf-8'))  # conservative upper bound for byte-based tokenizers
    def within_budget(indices):
        result, used = set(), 0
        for i in sorted(indices, key=lambda i: (-entries[i].get('priority', 0), entries[i]['insertion_order'], i)):
            size = cost(expand(entries[i]['content']))
            if used + size <= budget:
                result.add(i)
                used += size
        return result
    for _ in range(len(entries) + 1):
        matches = set(selected)
        for i, entry in enumerate(entries):
            if not entry['enabled']:
                continue
            text = source if entry.get('case_sensitive', False) else source.casefold()
            def hits(keys):
                return any((expand(k) if entry.get('case_sensitive', False) else expand(k).casefold()) in text for k in keys if k)
            if entry.get('constant', False) or (hits(entry['keys']) and (not entry.get('selective', False) or hits(entry.get('secondary_keys', [])))):
                matches.add(i)
        accepted = within_budget(matches)
        if accepted == selected:
            break
        selected = accepted
        if not book.get('recursive_scanning', False):
            break
        source = '\n'.join([base_source] + [expand(entries[i]['content']) for i in sorted(selected)])
    ordered = sorted(selected, key=lambda i: (entries[i]['insertion_order'], i))
    return tuple('\n'.join(expand(entries[i]['content']) for i in ordered if entries[i].get('position', 'before_char') == position)
                 for position in ('before_char', 'after_char'))


def merge_card_data(existing, updates):
    """Partial edits preserve unknown dictionaries and optional entry metadata."""
    result = deepcopy(existing)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_card_data(result[key], value)
        elif key == 'entries' and isinstance(value, list) and isinstance(result.get(key), list):
            old_entries = result[key]
            by_id = {e['id']: e for e in old_entries if isinstance(e, dict) and 'id' in e}
            merged = []
            for index, entry in enumerate(value):
                old = by_id.get(entry.get('id'), {}) if isinstance(entry, dict) and 'id' in entry else (old_entries[index] if index < len(old_entries) else {})
                merged.append(merge_card_data(old, entry) if isinstance(old, dict) and isinstance(entry, dict) else deepcopy(entry))
            result[key] = merged
        else:
            result[key] = deepcopy(value)
    return result


def read_legacy_card(document):
    """Repair known legacy representations in memory; leave source files intact."""
    data = deepcopy(document.get('data', document))
    if isinstance(data.get('alternate_greetings'), str):
        data['alternate_greetings'] = [data['alternate_greetings']] if data['alternate_greetings'] else []
    book = data.get('character_book')
    if isinstance(book, dict) and isinstance(book.get('entries'), list):
        for entry in book['entries']:
            if isinstance(entry, dict) and entry.get('position') == '':
                entry.pop('position')
    return normalize_card(data)
