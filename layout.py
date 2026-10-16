# SPDX-License-Identifier: GPL-3.0-only
import math
import torch
import torch.nn.functional as F

def effective_centers(characters):
    """Keep unique points; spread coincident groups horizontally in slot order."""
    points = [(c.x, c.y) for c in characters]
    result = list(points)
    groups = {}
    for i, point in enumerate(points):
        groups.setdefault(point, []).append(i)
    moved = []
    for (x, y), indices in groups.items():
        if len(indices) < 2:
            continue
        if len(indices) == len(points):
            xs = [(i + 0.5) / len(indices) for i in range(len(indices))]
        else:
            # A bounded neighborhood avoids moving unrelated, explicit positions.
            others = [p for p in points if p != (x, y)]
            radius = min(0.25, min(math.hypot(x - a, y - b) for a, b in others) / 3)
            left, right = max(0.0, x - radius), min(1.0, x + radius)
            xs = [left + (right - left) * (i + 0.5) / len(indices) for i in range(len(indices))]
        for index, new_x in zip(indices, xs):
            result[index] = (new_x, y)
        moved.append([i + 1 for i in indices])
    return tuple(result), moved

def region_masks(centers, width, height, feather):
    """Partition the canvas at latent resolution, then soften shared boundaries."""
    if any(isinstance(v, bool) or not isinstance(v, int) or not 64 <= v <= 4096 or v % 8
           for v in (width, height)):
        raise ValueError("Use dimensions divisible by 8, from 64 to 4096. / 크기는 64~4096의 8배수로 설정해 주세요.")
    if not isinstance(feather, (int, float)) or not math.isfinite(feather) or not 0 <= feather <= 0.25:
        raise ValueError("Region feather must be 0–0.25. / 영역 경계 여유는 0~0.25로 설정해 주세요.")
    h, w = height // 8, width // 8
    if not centers:
        return torch.ones((1, h, w))
    yy, xx = torch.meshgrid((torch.arange(h) + 0.5) / h, (torch.arange(w) + 0.5) / w, indexing="ij")
    distances = torch.stack([(xx - x).square() + (yy - y).square() for x, y in centers])
    owners = distances.argmin(dim=0)
    masks = torch.stack([(owners == i).float() for i in range(len(centers))])
    radius = round(min(h, w) * feather)
    if radius:
        masks = F.avg_pool2d(F.pad(masks[:, None], (radius,) * 4, mode="replicate"),
                             2 * radius + 1, stride=1)[:, 0]
    # Reject unrepresentable collocated regions rather than silently discard a character.
    if not all(bool(m.any()) for m in masks):
        raise ValueError("Character positions are too close at this resolution. Spread them farther apart or increase the size. / "
                         "현재 해상도에서 캐릭터 좌표가 너무 가깝습니다. 간격이나 이미지 크기를 늘려 주세요.")
    return masks / masks.sum(dim=0, keepdim=True).clamp_min(1e-8)
