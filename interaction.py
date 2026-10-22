# SPDX-License-Identifier: GPL-3.0-only
"""Extra self-attention separation only between exclusive character cells."""
import json
import math

from .routing import BoxGroups, weak_self_bias, hold_decay_spatial_separation


def interaction_settings(value):
    if value is None:
        return None
    try:
        d = json.loads(value) if isinstance(value, str) else value
        if not isinstance(d, dict) or d.get('preset') not in ('baseline', 'delay3', 'delay6', 'custom'):
            raise ValueError()
        delay, decrement = d.get('delay_steps', 6), d.get('decrement', .2)
        if type(delay) is not int or not 0 <= delay <= 30:
            raise ValueError()
        if isinstance(decrement, bool) or not isinstance(decrement, (int, float)) or not math.isfinite(decrement) or not .01 <= decrement <= 1:
            raise ValueError()
        return dict(preset=d['preset'], delay_steps=delay, decrement=decrement)
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid interaction settings. / 겹침 제어 설정을 확인해 주세요.') from error


def exclusive_schedule(config, progress, steps, initial, hold, decrement):
    if config is None or config['preset'] == 'baseline':
        return None
    delay = {'delay3': 3, 'delay6': 6}.get(config['preset'], config['delay_steps'])
    delta = config['decrement'] if config['preset'] == 'custom' else decrement
    return hold_decay_spatial_separation(progress, steps, initial, min(steps, hold+delay), delta)


def protected_self_bias(groups, size, reference, separation, exclusive=None):
    bias = weak_self_bias(groups, size, reference, separation)
    if exclusive is None or not isinstance(groups, BoxGroups):
        return bias
    if not 0 <= exclusive < 1:
        raise ValueError('Exclusive separation must be in [0, 1).')
    for owners, queries in groups.cells:
        if len(owners) != 1:
            continue
        for other, keys in groups.cells:
            if len(other) == 1 and other != owners:
                bias[queries[:, None], keys] = math.log1p(-exclusive)
    return bias


class RSMultiCharacterInteraction:
    @classmethod
    def INPUT_TYPES(cls):
        from .character_builder import BUILD_PIPE_TYPE
        return {'required': {
            'preset': (['baseline', 'delay3', 'delay6', 'custom'], {'default': 'baseline',
                'tooltip': 'Delay only non-overlapping character boundaries. Overlap and background keep the sampler schedule.'}),
            'delay_steps': ('INT', {'default': 6, 'min': 0, 'max': 30, 'tooltip': 'Custom only: extra scheduled steps before exclusive boundaries decay.'}),
            'decrement': ('FLOAT', {'default': .2, 'min': .01, 'max': 1., 'step': .01,
                'tooltip': 'Custom only: exclusive separation decrease per scheduled step.'}),
        }, 'optional': {'building_pipe': (BUILD_PIPE_TYPE,)}}

    from .character_builder import BUILD_PIPE_TYPE
    RETURN_TYPES = (BUILD_PIPE_TYPE,)
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Characters'
    DESCRIPTION = 'Anima/SDXL: preserve non-overlapping character separation longer while overlapping regions keep their normal schedule. Baseline preserves existing behavior. This guides identity separation, not exact pose or contact.'

    def apply(self, preset='baseline', delay_steps=6, decrement=.2, building_pipe=None):
        from dataclasses import replace
        from .character_builder import BuildPipe
        config = interaction_settings(dict(preset=preset, delay_steps=delay_steps, decrement=decrement))
        if building_pipe is not None and not isinstance(building_pipe, BuildPipe):
            raise ValueError('Connect an RS building pipe.')
        return (replace(building_pipe or BuildPipe(), interaction_json=json.dumps(config)),)
