# SPDX-License-Identifier: GPL-3.0-only
"""Accept native Anima LLLite hooks while preserving RS attention routing."""


def validate_model_patches(model, family):
    options = model.model_options.get('transformer_options', {})
    patches = options.get('patches', {})
    if not any(options.get(k) for k in ('patches', 'patches_replace', 'optimized_attention_override')):
        return False
    error = ('Only native Apply Anima LLLite pose patches are supported with RS routing. '
             'Remove other attention patches. / 기본 Apply Anima LLLite만 함께 사용할 수 있습니다. 다른 어텐션 패치를 분리해 주세요.')
    if family != 'Anima' or options.get('patches_replace') or options.get('optimized_attention_override'):
        raise ValueError(error)
    from comfy.ldm.anima.lllite import AnimaLLLitePatch, AnimaLLLiteAttentionPatch, AnimaLLLiteMLPPatch
    kinds = {'post_input': AnimaLLLitePatch, 'attn1_patch': AnimaLLLiteAttentionPatch,
             'attn2_patch': AnimaLLLiteAttentionPatch, 'mlp_patch': AnimaLLLiteMLPPatch}
    if set(patches) != set(kinds) or any(not values for values in patches.values()):
        raise ValueError(error)
    if any(type(p) is not kinds[key] for key, values in patches.items() for p in values):
        raise ValueError(error)
    roots = patches['post_input']
    for key in ('attn1_patch', 'attn2_patch', 'mlp_patch'):
        if [p.patch for p in patches[key]] != roots:
            raise ValueError('Incomplete Anima LLLite patch group. Reconnect Apply Anima LLLite.')
    expected = {'attn1_patch': {'q': 'self_attn_q_proj', 'k': 'self_attn_k_proj', 'v': 'self_attn_v_proj'},
                'attn2_patch': {'q': 'cross_attn_q_proj'}}
    for key, targets in expected.items():
        if any(p.targets != targets for p in patches[key]):
            raise ValueError(error)
    blocks = model.get_model_object('diffusion_model').blocks
    width = blocks[0].self_attn.q_proj.weight.shape[0]
    for patch in roots:
        adapter = patch.model_patch.model
        if adapter.block_count != len(blocks) or adapter.model_dim != width:
            raise ValueError('Anima pose adapter and base model have different block counts or dimensions. '
                             'Use matching weights; the tested 3D pose adapter is for Anima 2B. / '
                             '포즈 어댑터와 기본 모델의 구조가 다릅니다. 시험한 3D 포즈 어댑터는 Anima 2B용입니다.')
    return True


def patch_metadata(model):
    """Small settings audit; never serialize the conditioning image or weights."""
    return [dict(strength=p.strength, sigma_start=p.sigma_start, sigma_end=p.sigma_end,
                 image_size=[int(p.image.shape[2]), int(p.image.shape[1])],
                 block_count=p.model_patch.model.block_count, model_dim=p.model_patch.model.model_dim)
            for p in model.model_options['transformer_options']['patches']['post_input']]
