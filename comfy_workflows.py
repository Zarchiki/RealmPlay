"""Typed workflow substitution; only explicitly mapped inputs are changed."""
import copy
import re
from logic_set_engine import OrderedTagSet


FACE_IDENTITY_KEYWORDS = (
    "asian", "east asian", "southeast asian", "japanese", "korean", "chinese", "thai", "vietnamese", "filipina",
    "caucasian", "european", "american", "british", "french", "italian", "russian", "scandinavian", "nordic", "german", "czech",
    "latina", "hispanic", "brazilian", "indian", "arab", "middle eastern", "african", "black",
    "elf", "elven", "half-elf", "dark elf", "high elf", "demon", "succubus", "tiefling", "angel",
    "kitsune", "fox girl", "catgirl", "nekomimi", "kemonomimi", "vampire", "dragon girl", "oni", "fairy",
    "skin", "complexion", "pale", "fair-skinned", "porcelain", "ivory", "tanned", "tan", "sun-kissed", "olive", "dark-skinned", "ebony",
    "eyes", "eye", "iris", "irises", "pupils", "heterochromia", "slit pupils", "eyelashes", "lashes", "tareme", "tsurime", "sanpaku",
    "hair", "bangs", "sidelocks", "ahoge", "twintails", "twin tails", "ponytail", "braid", "braided", "bob cut", "hime cut", "bun", "blonde",
    "face", "facial", "freckles", "mole", "beauty mark", "scar", "fang", "fangs", "pointed ears", "elf ears", "glasses", "eyepatch",
    "horns", "halo", "animal ears", "cat ears", "fox ears", "lips", "cheek", "cheeks", "eyebrows", "earrings",
)

BODY_ONLY_EXCLUSIONS = (
    "breasts", "breast", "tits", "chest", "cleavage", "nipples", "areola",
    "waist", "hips", "thighs", "thigh", "legs", "ass", "butt", "booty",
    "pussy", "vagina", "penis", "cock", "anus", "anal", "barefoot", "feet", "toes",
    "skirt", "pants", "shorts", "jeans", "panties", "thong", "bra", "bikini",
    "stockings", "thighhighs", "shoes", "boots", "heels", "dress", "shirt", "blouse", "jacket", "coat",
    "full body", "cowboy shot", "wide shot", "from behind", "doggystyle", "cowgirl position",
)

GENERIC_EYE_OVERRIDES = (
    r"\brelaxed\s+eyes\b",
    r"\bbright\s+wide\s+eyes\b",
    r"\bwide\s+open\s+eyes\b",
    r"\bwide\s+eyes\b",
    r"\bbright\s+eyes\b",
    r"\bsparkling\s+eyes\b",
    r"\bdew-bright\s+eyes\b",
    r"\bluminous\s+eyes\b",
    r"\bsoft\s+luminous\s+eyes\b",
    r"\badoring\s+bright\s+eyes\b",
    r"\bfierce\s+glowing\s+eyes\b",
    r"\bexpressive\s+eyes\b",
    r"\bbeautiful\s+expressive\s+eyes\b",
    r"\bradiant\s+purple\s+eyes\b",
)


EYE_TRAIT_KEYWORDS = (
    "eyes", "eye", "iris", "irises", "pupils", "pupil",
    "heterochromia", "slit pupils", "tareme", "tsurime", "sanpaku",
)
EYE_TRAIT_EXCLUSIONS = (
    "eyebrow", "eyebrows", "eyepatch", "eyeglasses", "glasses", "eyeshadow", "eye mask", "eye contact", "looking", "closed eyes",
)


def extract_character_eye_tags(appearance_text):
    """Extract eye color and iris/pupil traits (e.g. 'deep blue eyes', 'amber eyes', 'heterochromia') from character appearance."""
    collected = []
    seen = set()
    for raw_chunk in re.split(r"[,;\n|]+", str(appearance_text or "")):
        tag = raw_chunk.strip(" .\t\r\n")
        if not tag:
            continue
        # Strip optional SD weights like (emerald green eyes:1.2) -> emerald green eyes
        clean_tag = re.sub(r"^\(+|\)+$", "", tag)
        clean_tag = re.sub(r":\d+(?:\.\d+)?$", "", clean_tag).strip()
        tl = clean_tag.casefold()
        if not tl or tl in seen or re.search(r"[\u0E00-\u0E7F]", tl):
            continue
        if any(excl in tl for excl in EYE_TRAIT_EXCLUSIONS):
            continue
        if any(re.search(rf"\b{re.escape(k)}\b", tl) for k in EYE_TRAIT_KEYWORDS):
            seen.add(tl)
            collected.append(clean_tag)
    return collected


def extract_facial_identity_tags(*prompt_sources):
    """Set-Theoretic Facial Identity Extraction:
    `(Appearance ∪ Positive) ∩ FACE_IDENTITY_KEYWORDS \\ BODY_ONLY_EXCLUSIONS`
    Note: '1girl', '1boy', 'solo', etc. are excluded to prevent ruining FaceDetailer crops.
    """
    raw_union = OrderedTagSet().union(*[s for s in prompt_sources if s])
    no_thai = raw_union.filter_by(lambda t: not re.search(r"[\u0E00-\u0E7F]", t))
    without_body = no_thai.subtract_patterns(BODY_ONLY_EXCLUSIONS)
    identity_set = without_body.filter_by(
        lambda t: t.casefold() not in {"1girl", "1boy", "2girls", "2boys", "solo", "female", "male"}
        and any(k in t.casefold() for k in FACE_IDENTITY_KEYWORDS)
    )
    return identity_set.to_list()


def build_default_workflow(values):
    """Build the maintenance-friendly standard txt2img API graph."""
    checkpoint = str(values.get('checkpoint') or '').strip()
    if not checkpoint:
        raise ValueError('Select a checkpoint in ComfyUI Image Gen settings')
    graph = {
        '1': {'class_type': 'CheckpointLoaderSimple', '_meta': {'title': 'Default Checkpoint'},
              'inputs': {'ckpt_name': checkpoint}},
        '2': {'class_type': 'CLIPTextEncode', '_meta': {'title': 'Positive Prompt'},
              'inputs': {'text': str(values.get('prompt', '')), 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', '_meta': {'title': 'Negative Prompt'},
              'inputs': {'text': str(values.get('negative_prompt', '')), 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', '_meta': {'title': 'Image Size'},
              'inputs': {'width': int(values.get('width', 576)),
                         'height': int(values.get('height', 1024)), 'batch_size': 1}},
        '5': {'class_type': 'KSampler', '_meta': {'title': 'Default Sampler'},
              'inputs': {'seed': int(values.get('seed', 0)), 'steps': int(values.get('steps', 25)),
                         'cfg': float(values.get('cfg', 7)),
                         'sampler_name': str(values.get('sampler') or 'euler'),
                         'scheduler': str(values.get('scheduler') or 'normal'),
                         'denoise': float(values.get('denoise', 1)), 'model': ['1', 0],
                         'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0]}},
        '6': {'class_type': 'VAEDecode', '_meta': {'title': 'Decode'},
              'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', '_meta': {'title': 'RealmPlay Output'},
              'inputs': {'filename_prefix': 'RealmPlay', 'images': ['6', 0]}},
    }
    selected_vae = str(values.get('vae') or '').strip()
    if selected_vae and selected_vae not in ('(Automatic / Built-in)', 'auto', 'default'):
        # Route custom external VAE into VAEDecode
        graph['8'] = {
            'class_type': 'VAELoader',
            '_meta': {'title': 'Custom VAE'},
            'inputs': {'vae_name': selected_vae}
        }
        graph['6']['inputs']['vae'] = ['8', 0]
    return graph




def validate_workflow(graph):
    if not isinstance(graph, dict) or not graph or 'nodes' in graph:
        raise ValueError('Import a ComfyUI API-format workflow, not the canvas JSON')
    if not all(isinstance(n, dict) and isinstance(n.get('inputs'), dict) and n.get('class_type') for n in graph.values()):
        raise ValueError('Invalid API workflow nodes')
    return graph


def compile_workflow(graph, values, mappings=None):
    graph = copy.deepcopy(validate_workflow(graph))
    mappings = mappings or {}
    def substitute(value):
        if isinstance(value, str):
            match = re.fullmatch(r'%([\w]+)%', value)
            if match:
                if match[1] not in values:
                    raise ValueError(f'Unknown placeholder: {match[1]}')
                return values[match[1]]
            return re.sub(r'%([\w]+)%', lambda m: str(values[m[1]]) if m[1] in values else m[0], value)
        if isinstance(value, list):
            return [substitute(v) for v in value]
        if isinstance(value, dict):
            return {k: substitute(v) for k, v in value.items()}
        return value
    graph = substitute(graph)
    for source, targets in mappings.items():
        if source not in values:
            raise ValueError(f'Unknown mapping source: {source}')
        for target in targets:
            try:
                node_id, field = str(target).split('.', 1)
            except ValueError:
                continue
            if node_id not in graph or field not in graph[node_id].get('inputs', {}):
                # When switching workflows (e.g. from CheckpointLoaderSimple to UNETLoader),
                # allow graceful fallback if mapping target is not in the active workflow.
                continue
            graph[node_id]['inputs'][field] = values[source]
    # A model selection is meaningful only when this particular workflow has
    # an explicit, valid checkpoint mapping.  Without that guard, selecting a
    # UNET-based workflow would overwrite its bundled UNET with the checkpoint
    # selected for a CheckpointLoaderSimple workflow.
    checkpoint_is_mapped = any(
        len(parts := str(target).split('.', 1)) == 2
        and parts[0] in graph
        and parts[1] in graph[parts[0]].get('inputs', {})
        for target in mappings.get('checkpoint', [])
    )
    # Wildcard nodes: map titles to values (positive, negative, emotion, suffix)
    titles = {
        'positive': 'prompt', 'aurelia_positive': 'prompt',
        'negative': 'negative_prompt', 'aurelia_negative': 'negative_prompt',
        'emotion': 'emotion', 'aurelia_emotion': 'emotion',
        'suffix': 'suffix', 'hidden': 'suffix', 'aurelia_hidden': 'suffix',
    }
    appearance_src = str(values.get('appearance') or '').strip()
    identity_tags = extract_facial_identity_tags(appearance_src) if appearance_src else extract_facial_identity_tags(values.get('prompt', ''))
    has_eye_color = any("eye" in t.casefold() or "iris" in t.casefold() or "heterochromia" in t.casefold() for t in identity_tags)
    for node in graph.values():
        if node['class_type'] == 'ImpactWildcardProcessor':
            inputs = node['inputs']
            source = titles.get(node.get('_meta', {}).get('title', '').lower())
            if source == 'emotion':
                inputs['mode'] = 'populate'
            if 'populated_text' in inputs:
                inputs['populated_text'] = ''
            if source and 'wildcard_text' in inputs:
                inputs['wildcard_text'] = str(values.get(source, ''))
        elif node['class_type'] == 'StringConcatenate' and node.get('_meta', {}).get('title', '').strip().lower() == 'facial pos':
            inputs = node['inputs']
            quality_part = str(inputs.get('string_b') or 'extreme detailed face, very high detailed facial features, detailed irises, detailed pupils').strip(' ,')
            if isinstance(inputs.get('string_a'), list):
                inputs['string_b'] = ', '.join([*identity_tags, quality_part]) if identity_tags else quality_part
                inputs['delimiter'] = ', '
            else:
                emo_val = str(values.get('emotion', '')).strip(' ,')
                parts = [*identity_tags, *([emo_val] if emo_val else []), quality_part]
                inputs['string_a'] = ', '.join(parts)
                inputs['string_b'] = ''
                inputs['delimiter'] = ''
        elif node['class_type'] == 'Image Saver Metadata':
            # Imported graphs may accidentally wire EMOTION into modelname.
            # Image Saver treats every comma-separated entry as a checkpoint.
            selected_ckpt = str(values.get('checkpoint') or '').strip()
            # Metadata is descriptive only, so it must always show the UI's
            # selected checkpoint even for a UNET-based workflow.  The guard
            # above still protects actual model-loader nodes from replacement.
            if selected_ckpt and 'modelname' in node['inputs']:
                node['inputs']['modelname'] = selected_ckpt
        elif node['class_type'] == 'UNETLoader':
            inputs = node.get('inputs', {})
            selected_ckpt = str(values.get('checkpoint') or '').strip()
            if checkpoint_is_mapped and selected_ckpt and 'unet_name' in inputs:
                inputs['unet_name'] = selected_ckpt
        elif node['class_type'] == 'CheckpointLoaderSimple':
            inputs = node.get('inputs', {})
            selected_ckpt = str(values.get('checkpoint') or '').strip()
            if checkpoint_is_mapped and selected_ckpt and 'ckpt_name' in inputs:
                inputs['ckpt_name'] = selected_ckpt
        elif node['class_type'] == 'VAELoader':
            inputs = node.get('inputs', {})
            selected_vae = str(values.get('vae') or '').strip()
            # If user selected an explicit external VAE (not empty and not Automatic), inject it
            if selected_vae and selected_vae not in ('(Automatic / Built-in)', 'auto', 'default'):
                if 'vae_name' in inputs:
                    inputs['vae_name'] = selected_vae
        elif node['class_type'] == 'CLIPLoader':
            inputs = node.get('inputs', {})
            selected_clip = str(values.get('clip') or '').strip()
            if selected_clip and selected_clip not in ('(Automatic / From Workflow)', 'auto', 'default'):
                if 'clip_name' in inputs:
                    inputs['clip_name'] = selected_clip
        elif node['class_type'] == 'SAMLoader':
            inputs = node.get('inputs', {})
            selected_sam = str(values.get('sam_model') or '').strip()
            if selected_sam and selected_sam not in ('(Automatic / From Workflow)', 'auto', 'default'):
                if 'model_name' in inputs:
                    inputs['model_name'] = selected_sam
        elif node['class_type'] == 'FaceDetailer':
            inputs = node.get('inputs', {})
            # Ensure FaceDetailer sampler and scheduler synchronize with selected generation parameters if available
            selected_sampler = str(values.get('sampler') or '').strip()
            selected_scheduler = str(values.get('scheduler') or '').strip()
            if selected_sampler and 'sampler_name' in inputs:
                inputs['sampler_name'] = selected_sampler
            if selected_scheduler and 'scheduler' in inputs:
                inputs['scheduler'] = selected_scheduler
    return graph


