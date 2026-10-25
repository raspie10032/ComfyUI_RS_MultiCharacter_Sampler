"""Validate and execute both camera entries in the actual CPU ComfyUI executor.

Usage: python tests/verify_builder_order_graph.py --comfy /path/ComfyUI --nai /path/NAI
No sampling, model download or real HTTP request is performed.
"""
import argparse
import asyncio
from contextlib import ExitStack
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy', type=Path, required=True)
    parser.add_argument('--nai', type=Path, required=True)
    options = parser.parse_args()
    sys.argv[:] = [sys.argv[0], '--cpu']
    sys.path.insert(0, str(options.comfy.resolve()))
    from comfy.cli_args import args
    args.cpu = True
    import nodes
    import execution
    import folder_paths

    def load(name, root):
        spec = importlib.util.spec_from_file_location(name, root/'__init__.py',
                                                     submodule_search_locations=[str(root)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
        nodes.NODE_CLASS_MAPPINGS.update(package.NODE_CLASS_MAPPINGS)
        return package

    load('_rs_builder_order_mc', Path(__file__).resolve().parents[1])
    load('_rs_builder_order_nai', options.nai.resolve())
    bridge = sys.modules['_rs_builder_order_nai.local_bridge']
    results, expected = [], []

    class Sink:
        OUTPUT_NODE = True
        RETURN_TYPES = ()
        FUNCTION = 'check'

        @classmethod
        def INPUT_TYPES(cls):
            return {'required': {'building_pipe': ('RS_MC_CHARACTER_PIPE,NAI_CONTEXT',)}}

        def check(self, building_pipe):
            record = building_pipe.rs_context_record()
            assert len(building_pipe.characters) == 2
            assert building_pipe.characters[0].region_mask is not None
            assert building_pipe.characters[1].bbox is not None
            assert len(building_pipe.text_regions) == 1
            assert 'from above' in building_pipe.prompt
            # The NAI receiver reads the same finalized captions and positions.
            chars = bridge.prepare_characters('nai-diffusion-5-full', building_pipe)
            assert len(chars) == 2
            if expected:
                assert record == expected[0]
            else:
                expected.append(record)
            results.append([c.x for c in building_pipe.characters])
            return ()

    nodes.NODE_CLASS_MAPPINGS['_RSBuilderOrderSink'] = Sink

    def node(kind, **values):
        fields = {}
        for name, spec in nodes.NODE_CLASS_MAPPINGS[kind].INPUT_TYPES().get('required', {}).items():
            config = spec[1] if len(spec) > 1 else {}
            if 'default' in config:
                fields[name] = config['default']
            elif isinstance(spec[0], list) and spec[0]:
                fields[name] = spec[0][0]
        return {'class_type': kind, 'inputs': fields | values}

    drawing = json.dumps({'version':1,'width':128,'height':128,'layers':{
        '1':{'strokes':[{'tool':'brush','size':.2,'points':[[.3,.2],[.3,.8]]}]}}})
    server = SimpleNamespace(client_id=None, last_node_id=None, send_sync=lambda *a: None)
    with ExitStack() as stack, tempfile.TemporaryDirectory() as root:
        stack.enter_context(patch('requests.sessions.Session.request', side_effect=AssertionError('HTTP disabled')))
        stack.enter_context(patch.object(folder_paths, 'get_temp_directory', return_value=root))
        for camera in ('RSCameraControl', 'NAICameraControl'):
            for order in itertools.permutations(('prompt','position','camera')):
                for alias in ('building_pipe', 'context'):
                    graph, previous = {}, None
                    for role in ('lora','draw','interaction',*order):
                        values = {
                            'prompt': ('RSMultiCharacterPrompt', dict(character_count=3,
                                character1='brown hair',character2='pink hair',
                                character3_kind='text',character3='HELLO')),
                            'position': ('RSMultiCharacterPosition', dict(character_count=3,
                                character2_geometry='box',character2_x=.72,character2_width=.2,
                                character2_height=.5,character3_geometry='box',character3_y=.12,
                                character3_width=.5,character3_height=.1,
                                mask_transforms='{"1":[0.03,0.04,1.1]}')),
                            'camera': (camera, dict(base_prompt='two people in a garden',
                                layout_sync='perspective',azimuth=25.,elevation=15.,
                                distance=.65,roll=12.,canvas_aspect=1.5)),
                            'lora': ('RSMultiCharacterLoRA', dict(character_count=2)),
                            'draw': ('RSMultiCharacterMaskDraw', dict(drawing=drawing,margin=0.)),
                            'interaction': ('RSMultiCharacterInteraction', dict(preset='delay6')),
                        }
                        kind, inputs = values[role]
                        if previous is not None:
                            inputs[alias if role=='camera' else 'building_pipe'] = [previous,0]
                        previous = str(len(graph)+1)
                        graph[previous] = node(kind, **inputs)
                    graph['7'] = node('RSMultiCharacterFinalize',building_pipe=[previous,0])
                    graph['8'] = node('_RSBuilderOrderSink',building_pipe=['7',0])
                    prompt_id = 'builder-order-'+str(len(results))
                    valid = asyncio.run(execution.validate_prompt(prompt_id, graph, None))
                    assert valid[0], valid
                    executor = execution.PromptExecutor(server, cache_args={'ram':0,'ram_inactive':0})
                    before = len(results)
                    executor.execute(graph, prompt_id, execute_outputs=valid[2])
                    assert executor.success and len(results)==before+1, executor.status_messages
    assert len(results) == 24
    print(json.dumps({'status':'passed','executed_graphs':len(results),
        'cameras':['RSCameraControl','NAICameraControl'],'legacy_alias':True,
        'native_nai_receiver':True,'real_http_requests':0}))


if __name__ == '__main__':
    main()
