"""Typed workflow substitution; only explicitly mapped inputs are changed."""
import copy
import re


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
    for source, targets in (mappings or {}).items():
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
    # Wildcard nodes: map titles to values (positive, negative, emotion, suffix)
    titles = {
        'positive': 'prompt', 'aurelia_positive': 'prompt',
        'negative': 'negative_prompt', 'aurelia_negative': 'negative_prompt',
        'emotion': 'emotion', 'aurelia_emotion': 'emotion',
        'suffix': 'suffix', 'hidden': 'suffix', 'aurelia_hidden': 'suffix',
    }
    for node in graph.values():
        if node['class_type'] == 'ImpactWildcardProcessor':
            inputs = node['inputs']
            if 'populated_text' in inputs:
                inputs['populated_text'] = ''
            source = titles.get(node.get('_meta', {}).get('title', '').lower())
            if source and 'wildcard_text' in inputs:
                inputs['wildcard_text'] = values.get(source, '')
        elif node['class_type'] == 'UNETLoader':
            inputs = node.get('inputs', {})
            selected_ckpt = str(values.get('checkpoint') or '').strip()
            if selected_ckpt and 'unet_name' in inputs:
                inputs['unet_name'] = selected_ckpt
        elif node['class_type'] == 'CheckpointLoaderSimple':
            inputs = node.get('inputs', {})
            selected_ckpt = str(values.get('checkpoint') or '').strip()
            if selected_ckpt and 'ckpt_name' in inputs:
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
    return graph


