# SPDX-License-Identifier: GPL-3.0-only
"""Coordinate-based attention connectivity for the private Anima experiment.

Routing selects Q/K/V rows BEFORE softmax. It is mathematically equivalent to
block masks with -inf for forbidden keys, without allocating an S x S mask.
No learned weights, prompt rewriting, or attention-output interpolation.
"""
from contextlib import contextmanager
import math
import torch
import torch.nn.functional as F


@contextmanager
def installed_ops(blocks, cross, spatial):
    """Only instance-local ops change; restore even when sampling raises."""
    previous = []
    try:
        for block in blocks:
            for name, replacement in (("cross_attn", cross), ("self_attn", spatial)):
                if replacement is None:
                    continue
                module = getattr(block, name)
                previous.append((module, module.attn_op))
                module.attn_op = replacement
        yield
    finally:
        for module, original in reversed(previous):
            module.attn_op = original


def token_owners(masks, height, width):
    if masks.ndim != 3 or not 1 <= masks.shape[0] <= 10:
        raise ValueError("Expected 1–10 spatial masks")
    if not torch.isfinite(masks).all() or (masks < 0).any():
        raise ValueError("Masks must be finite and nonnegative")
    resized = F.interpolate(masks[:, None].float(), (height, width), mode="area")[:, 0]
    if (resized.sum(0) <= 0).any():
        raise ValueError("The coordinate partition must cover the canvas")
    owners = resized.argmax(0).flatten()
    if owners.unique().numel() != len(masks):
        raise ValueError("A character has no image tokens at this resolution")
    return owners


class BoxGroups(list):
    """Character membership plus disjoint cells; each query is written once."""
    def __init__(self, groups, cells, background):
        super().__init__(groups)
        self.cells, self.background = cells, background


def token_groups(masks, height, width, device=None, boxes=False):
    """boxes=True: all boxes; tuple[bool]: per-slot box/point geometry.

    In a mixed layout, explicit boxes win at each attention resolution. Outside
    them, exactly one point owns a token, using the legacy argmax partition.
    """
    if not boxes:
        owners = token_owners(masks, height, width).to(device)
        return [(owners == i).nonzero().flatten() for i in range(len(masks))]
    if (masks.ndim != 3 or not 1 <= len(masks) <= 10 or
            not torch.isfinite(masks).all() or (masks < 0).any()):
        raise ValueError("Expected 1–10 finite, nonnegative box masks.")
    coverage = F.interpolate(masks[:, None].float(), (height, width), mode="area")[:, 0].flatten(1)
    membership = coverage > 1e-6
    if isinstance(boxes, tuple):
        if len(boxes) != len(masks) or any(type(v) is not bool for v in boxes):
            raise ValueError("Expected one box/point flag per region.")
        point_ids = [i for i, is_box in enumerate(boxes) if not is_box]
        box_ids = [i for i, is_box in enumerate(boxes) if is_box]
        if point_ids:
            occupied = membership[box_ids].any(0) if box_ids else torch.zeros_like(membership[0])
            owners = coverage[point_ids].argmax(0)
            for point, slot in enumerate(point_ids):
                membership[slot] = (owners == point) & ~occupied & (coverage[slot] > 1e-6)
    if not membership.any(1).all():
        raise ValueError("A region has no image tokens. Boxes may fully cover a point region; reduce/move them, spread the points, or increase image size. / 상자가 좌표 영역을 완전히 덮었거나 영역이 너무 작습니다. 상자 크기·위치나 좌표 간격을 조정해 주세요.")
    codes = (membership.long() * (2 ** torch.arange(len(masks)))[:, None]).sum(0)
    cells = [(tuple(i for i in range(len(masks)) if code & (1 << i)),
              (codes == code).nonzero().flatten().to(device)) for code in codes.unique().tolist()]
    groups = [row.nonzero().flatten().to(device) for row in membership]
    return BoxGroups(groups, cells, (codes == 0).nonzero().flatten().to(device))


def box_cross(q, k, v, groups, lengths, kinds, weights, character_gain, include_common, common_tokens):
    offsets = [0]
    for length in lengths:
        offsets.append(offsets[-1] + length)
    if any(length <= 0 for length in lengths):
        raise ValueError("Every caption needs at least one text token.")
    common_end = lengths[0] if common_tokens is None else common_tokens
    if not 1 <= common_end <= lengths[0]:
        raise ValueError("Invalid common text token count")
    if weights is not None and (not include_common or len(weights) != 2 or
            any(not math.isfinite(w) for w in weights) or weights[0] < 0 or weights[1] <= 0):
        raise ValueError("Common weight must be nonnegative; character weight must be positive")
    result = q.new_empty(q.shape[:2] + (q.shape[2] * q.shape[3],))
    for batch, kind in enumerate(kinds):
        qb, kb, vb = q[batch:batch+1], k[batch:batch+1], v[batch:batch+1]
        if kind == 1:
            result[batch:batch+1] = sdpa(qb, kb[:, :lengths[0]], vb[:, :lengths[0]])
            continue
        if kind != 0:
            raise ValueError("Unsupported CFG condition kind")
        for members, indices in groups.cells:
            if not members:
                # A zero early common prior only applies inside character boxes.
                result[batch:batch+1, indices] = sdpa(qb[:, indices], kb[:, :common_end], vb[:, :common_end])
                continue
            end = common_end if include_common else 0
            keys, values = [kb[:, :end]], [vb[:, :end]]
            bias_parts = []
            if weights is not None:
                bias_parts.append(q.new_full((end,), -torch.inf if weights[0] == 0 else math.log(weights[0] / end)))
            for slot in members:
                start, stop = offsets[slot+1], offsets[slot+2]
                keys.append(kb[:, start:stop])
                values.append(vb[:, start:stop] * character_gain)
                if weights is not None:
                    # Share total character prior equally, independent of text length.
                    bias_parts.append(q.new_full((stop-start,), math.log(weights[1] / (len(members)*(stop-start)))))
            bias = torch.cat(bias_parts)[None, :] if weights is not None else None
            result[batch:batch+1, indices] = sdpa(qb[:, indices], torch.cat(keys, 1), torch.cat(values, 1), bias)
    return result


def sdpa(q, k, v, bias=None):
    # Anima input/output: B,S,H,D -> B,S,H*D.
    return F.scaled_dot_product_attention(
        q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2),
        dropout_p=0.0, attn_mask=bias,
    ).transpose(1, 2).flatten(2)


def route_cross(q, k, v, groups, text_lengths, kinds, include_common=True, weights=None, common_tokens=None, character_gain=1.):
    """Positive: common text + owning character. Negative: original text only.

    Common text remains globally available, but is not a spatial/person slot.
    Each character is encoded/adapted independently before concatenating keys.
    character_gain scales only the owning character's V contribution, leaving
    Q/K and the common prior unchanged. It is not a softmax group weight.
    """
    if len(kinds) != q.shape[0] or len(text_lengths) != len(groups) + 1:
        raise ValueError("Invalid CFG batch or character/text layout")
    if sum(text_lengths) != k.shape[1] or k.shape != v.shape:
        raise ValueError("Text key/value layout mismatch")
    if not math.isfinite(character_gain) or not 1 <= character_gain <= 3:
        raise ValueError("Character value gain must be finite and in [1, 3]")
    if isinstance(groups, BoxGroups):
        return box_cross(q, k, v, groups, text_lengths, kinds, weights,
                         character_gain, include_common, common_tokens)
    offsets = [text_lengths[0]]
    for length in text_lengths[1:]:
        offsets.append(offsets[-1] + length)
    result = q.new_empty(q.shape[:2] + (q.shape[2] * q.shape[3],))
    for batch, kind in enumerate(kinds):
        qb, kb, vb = q[batch:batch+1], k[batch:batch+1], v[batch:batch+1]
        if kind == 1:
            result[batch:batch+1] = sdpa(qb, kb[:, :text_lengths[0]], vb[:, :text_lengths[0]])
        elif kind == 0:
            for slot, indices in enumerate(groups):
                common_end = text_lengths[0] if include_common else 0
                if include_common and common_tokens is not None:
                    if not 1 <= common_tokens <= common_end:
                        raise ValueError("Invalid common text token count")
                    common_end = common_tokens
                keys = torch.cat((kb[:, :common_end], kb[:, offsets[slot]:offsets[slot+1]]), 1)
                character_values = vb[:, offsets[slot]:offsets[slot+1]]
                if character_gain != 1.:
                    character_values = character_values * character_gain
                values = torch.cat((vb[:, :common_end], character_values), 1)
                bias = None
                if weights is not None:
                    if (not include_common or len(weights) != 2
                            or any(not math.isfinite(w) for w in weights)
                            or weights[0] < 0 or weights[1] <= 0):
                        raise ValueError("Common weight must be nonnegative; character weight must be positive")
                    # A log prior acts BEFORE softmax; normalize by group length
                    # so a long common prompt cannot win just by having more keys.
                    bias = q.new_empty(keys.shape[1])
                    # Exact ablation: zero excludes common keys from softmax.
                    # Do not approximate zero with epsilon or empty text.
                    bias[:common_end] = -torch.inf if weights[0] == 0 else math.log(weights[0] / common_end)
                    bias[common_end:] = math.log(weights[1] / text_lengths[slot+1])
                result[batch:batch+1, indices] = sdpa(qb[:, indices], keys, values, None if bias is None else bias[None, :])
        else:
            raise ValueError("Unsupported CFG condition kind")
    return result


def route_self(q, k, v, groups):
    """Block spatial information exchange across character partitions.

    Applied to positive AND negative branches so the spatial prior is consistent
    on both sides of CFG. The global text remains available through cross-attn.
    """
    if q.shape != k.shape or k.shape != v.shape:
        raise ValueError("Self-attention requires matching Q/K/V")
    result = q.new_empty(q.shape[:2] + (q.shape[2] * q.shape[3],))
    for indices in groups:
        result[:, indices] = sdpa(q[:, indices], k[:, indices], v[:, indices])
    return result


def weak_self_bias(groups, size, reference, separation=0.2):
    """20% separation = foreign keys retain 80% of their pre-softmax prior.

    Not a 20% output blend and not a claim about measured attention mass.
    Applied equally to both CFG branches. Self/own keys remain unpenalized.
    """
    if not 0 <= separation < 1:
        raise ValueError("Weak spatial separation must be in [0, 1)")
    bias = reference.new_full((size, size), math.log1p(-separation))
    for group in groups:
        bias[group[:, None], group] = 0
    if isinstance(groups, BoxGroups):
        # Background remains a shared scene; overlapping boxes share spatial keys.
        bias[groups.background, :] = 0
        bias[:, groups.background] = 0
    return bias


def common_weight(progress, initial=0.05):
    """First 40%: initial; smooth increase; last 25%: 1. Character prior = 1."""
    if not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError("Denoising progress must be in [0, 1]")
    if not math.isfinite(initial) or not 0 <= initial <= 1:
        raise ValueError("Initial common prior must be in [0, 1]")
    t = min(1., max(0., (progress - .4) / .35))
    return initial + (1 - initial) * t * t * (3 - 2 * t)


def character_value_gain(progress, initial=1.):
    """Early 40% at initial gain, smooth return to 1 by 75%, then unchanged.

    Scales V rather than the group prior: increasing the latter would merely
    lower the effective common/character ratio in the same softmax.
    """
    if not math.isfinite(initial) or not 1 <= initial <= 3:
        raise ValueError("Initial character value gain must be in [1, 3]")
    ramp = common_weight(progress, .5)
    return 1. + (initial - 1.) * (2. - 2. * ramp)


def stepped_common_weight(progress, evaluation_count, initial=0., increment=.1, after_step3_boost=0.):
    """Increase the common prior every three sampler steps, capped at 1.

    Use position in the actual sigma schedule, never forward-call count.
    Steps 1-3 use initial; 4-6 use initial+increment. With increment .2,
    a zero start reaches 1 at step 16 and stays there.
    A tiny tolerance prevents floating point roundoff at exact boundaries.
    """
    common_weight(progress, initial)  # shared finite/range validation
    if type(evaluation_count) is not int or evaluation_count < 2:
        raise ValueError("Expected at least two sampler evaluations")
    if not math.isfinite(increment) or not 0 < increment <= 1:
        raise ValueError("Common increment must be finite and in (0, 1]")
    if not math.isfinite(after_step3_boost) or not 0 <= after_step3_boost <= 1:
        raise ValueError("Post-step-3 common boost must be finite and in [0, 1]")
    step = math.floor(progress * (evaluation_count - 1) + 1e-6)
    # Preserve the exact previous arithmetic for the default .1 schedule.
    base = initial + (step // 3) / 10. * (increment / .1)
    return min(1., base + (after_step3_boost if step >= 3 else 0.))


def spatial_separation(progress, initial=.2, late=.2):
    """Hold through 40%, smoothly interpolate until 75%, then hold late.

    Separation sets a foreign-key prior of 1-separation on BOTH CFG branches;
    it is not the total fraction of attention crossing the region boundary.
    """
    if any(not math.isfinite(s) or not 0 <= s < 1 for s in (initial, late)):
        raise ValueError("Spatial separation endpoints must be finite and in [0, 1)")
    ramp = common_weight(progress, 0.)
    return initial + (late - initial) * ramp


def stepped_spatial_separation(progress, evaluation_count, initial=.9, decrement=.1):
    """Reduce separation every three sampler steps, clamping at zero.

    Uses the same sigma-derived step position as the common-prior staircase.
    Zero removes only the self-attention bias; cross-attention ownership stays.
    """
    spatial_separation(progress, initial, 0.)  # shared finite/range validation
    if not math.isfinite(decrement) or not 0 < decrement <= 1:
        raise ValueError("Separation decrement must be finite and in (0, 1]")
    staircase = stepped_common_weight(progress, evaluation_count, 0.)
    remaining = initial - staircase * (decrement / .1)
    # Decimal steps such as .9 - 3 * .3 must release the bias exactly.
    return 0. if remaining < 1e-12 else remaining


def hold2_decay_spatial_separation(progress, evaluation_count, initial=.9, decrement=.4):
    """Hold steps 1-2, subtract decrement each step from step 3, clamp at zero.

    Uses the actual sigma schedule position, so repeated CFG forwards do not
    advance the decay. Cross-attention ownership is unaffected.
    """
    spatial_separation(progress, initial, 0.)
    if type(evaluation_count) is not int or evaluation_count < 2:
        raise ValueError("Expected at least two sampler evaluations")
    if not math.isfinite(decrement) or not 0 < decrement <= 1:
        raise ValueError("Separation decrement must be finite and in (0, 1]")
    step = math.floor(progress * (evaluation_count - 1) + 1e-6)
    remaining = initial - max(0, step - 1) * decrement
    return 0. if remaining < 1e-12 else remaining


def hold_decay_spatial_separation(progress, evaluation_count, initial=.9, hold_steps=3, decrement=.2):
    """Hold N full evaluations, then decay per evaluation; CFG calls do not advance it."""
    spatial_separation(progress, initial, 0.)
    if type(evaluation_count) is not int or evaluation_count < 2:
        raise ValueError("Expected at least two sampler evaluations")
    if type(hold_steps) is not int or not 1 <= hold_steps <= evaluation_count:
        raise ValueError("Hold steps must be an integer within the evaluation schedule")
    if not math.isfinite(decrement) or not 0 < decrement <= 1:
        raise ValueError("Separation decrement must be finite and in (0, 1]")
    step = math.floor(progress * (evaluation_count - 1) + 1e-6)
    remaining = initial - max(0, step + 1 - hold_steps) * decrement
    return 0. if remaining < 1e-12 else remaining


def release_step2_spatial_separation(progress, evaluation_count, initial=.9):
    """Keep separation for step 1, remove all self-attention bias from step 2.

    The full reference sigma schedule determines the second model evaluation;
    repeated CFG forwards do not advance it. Cross-attention ownership stays.
    """
    spatial_separation(progress, initial, 0.)
    if type(evaluation_count) is not int or evaluation_count < 2:
        raise ValueError("Expected at least two sampler evaluations")
    step = math.floor(progress * (evaluation_count - 1) + 1e-6)
    return initial if step == 0 else 0.


def staged_character_gain(progress, early=1.3, middle=1.5, late=1.7):
    """Piecewise V gain: first 40%, middle to 75%, final 25%.

    Progress comes from actual evaluation sigmas, not a callback counter.
    With 30 evaluations this selects 12 early, 10 middle, and 8 late steps.
    """
    if not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError("Denoising progress must be in [0, 1]")
    if any(not math.isfinite(v) or not 1 <= v <= 3 for v in (early, middle, late)):
        raise ValueError("Character value gains must be finite and in [1, 3]")
    return early if progress < .4 else middle if progress < .75 else late


def sigma_progress(sigma, sigmas):
    """Position within the actual nonzero sampler schedule, not 1-sigma.

    Interpolate intermediate solver evaluations; repeated CFG forwards at the
    same sigma get exactly the same schedule value. The final zero is not a
    model evaluation and must be omitted by the caller.
    """
    if len(sigmas) < 2 or any(a <= b for a, b in zip(sigmas, sigmas[1:])):
        raise ValueError("Expected at least two strictly descending evaluation sigmas")
    if not math.isfinite(sigma):
        raise ValueError("Sigma must be finite")
    if sigma >= sigmas[0]:
        return 0.
    if sigma <= sigmas[-1]:
        return 1.
    for i, (a, b) in enumerate(zip(sigmas, sigmas[1:])):
        if a >= sigma >= b:
            return (i + (a - sigma) / (a - b)) / (len(sigmas) - 1)
    raise ValueError("Sigma is outside the sampler schedule")
