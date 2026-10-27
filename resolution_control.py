# SPDX-License-Identifier: GPL-3.0-only
"""Resolution-aware exclusive boundaries, scoped to the progressive sampler."""
import math


def separation_for_grid(config, grid, initial, scheduled, exclusive):
    if config is None:
        return exclusive, None
    final = config['final_grid']
    if len(grid) != 2 or len(final) != 2 or min(*grid, *final) <= 0:
        raise ValueError('Invalid progressive attention grid.')
    ratio = math.prod(grid) / math.prod(final)
    if not 0 < ratio <= 1:
        raise ValueError('Progressive attention grid exceeds the final resolution.')
    floor = .99 if ratio < 1 else 0.
    result = max(scheduled, floor, 0. if exclusive is None else exclusive) if ratio < 1 else exclusive
    return result, dict(area_ratio=ratio, floor=floor, scheduled=scheduled, applied_exclusive=result)
