# SPDX-License-Identifier: GPL-3.0-only
"""Identical spatial logit priors, stored once per ownership cell.

Reference queries retain unrestricted access to all keys, just as with the
zero-padded dense bias. This does not cache changing image features or alter
the target/reference connectivity learned by the adapter.
"""
from dataclasses import dataclass
import math
import torch

from .routing import BoxGroups, sdpa


@dataclass
class CompactBias:
    cells: list
    rows: torch.Tensor
    size: int
    total: int

    def at(self, query, key):
        query = int(query)
        if query >= self.size:
            return 0.
        for row, (_, indices) in zip(self.rows, self.cells):
            if (indices == query).any():
                return float(row[int(key)])
        raise ValueError('Missing spatial query cell.')


def compact_bias(groups, size, total, reference, separation, exclusive=None):
    if not 0 <= separation < 1 or total < size:
        raise ValueError('Invalid spatial separation or reference token count.')
    if exclusive is not None and not 0 <= exclusive < 1:
        raise ValueError('Exclusive separation must be in [0, 1).')
    cells = groups.cells if isinstance(groups, BoxGroups) else [
        ((i,), indices) for i, indices in enumerate(groups)]
    rows = reference.new_zeros((len(cells), total))
    for row, (owners, _) in zip(rows, cells):
        if not owners:
            continue
        row[:size] = math.log1p(-separation)
        for owner in owners:
            row[groups[owner]] = 0
        if isinstance(groups, BoxGroups):
            row[groups.background] = 0
            if exclusive is not None and len(owners) == 1:
                for other, keys in cells:
                    if len(other) == 1 and other != owners:
                        row[keys] = math.log1p(-exclusive)
    return CompactBias(cells, rows, size, total)


def compact_attention(q, k, v, bias):
    if q.shape[1] != bias.total or k.shape != v.shape or k.shape[1] != bias.total:
        raise ValueError('Compact reference attention token layout mismatch.')
    out = q.new_empty((*q.shape[:2], q.shape[2]*q.shape[3]))
    for row, (_, indices) in zip(bias.rows, bias.cells):
        if len(indices):
            out[:, indices] = sdpa(q[:, indices], k, v, row[None, :])
    if bias.total > bias.size:
        out[:, bias.size:] = sdpa(q[:, bias.size:], k, v)
    return out
