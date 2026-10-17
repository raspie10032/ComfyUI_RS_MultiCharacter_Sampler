# SPDX-License-Identifier: GPL-3.0-only
import math
import json
import torch
import torch.nn.functional as F

def effective_centers(characters):
    """Keep unique points; spread coincident groups horizontally in slot order."""
    points = [(c.x, c.y) for c in characters]
    if any(c.bbox is not None for c in characters):
        indices = [i for i, c in enumerate(characters) if c.bbox is None]
        if not indices:
            return tuple(points), []  # Coincident boxes are intentional overlaps.
        adjusted, moved = effective_centers([characters[i] for i in indices])
        for i, center in zip(indices, adjusted):
            points[i] = center
        return tuple(points), [[indices[i-1]+1 for i in group] for group in moved]
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


def character_masks(characters, centers, width, height, feather):
    if not any(c.bbox is not None for c in characters):
        return region_masks(centers, width, height, feather)
    region_masks((), width, height, feather)  # Shared dimension validation.
    point_ids = [i for i, c in enumerate(characters) if c.bbox is None]
    points = iter(region_masks([centers[i] for i in point_ids], width, height, feather)) if point_ids else iter(())
    h, w = height // 8, width // 8
    xx, yy = torch.arange(w) / w, torch.arange(h) / h
    masks = []
    for c in characters:
        if c.bbox is None:
            masks.append(next(points))
            continue
        left, top, right, bottom = c.bbox
        # Exact fractional coverage. Downstream area resize keeps small boxes
        # representable; boxes touching a token share it, without argmax ties.
        horizontal = (torch.minimum(xx + 1/w, torch.tensor(right)) - torch.maximum(xx, torch.tensor(left))).clamp_min(0) * w
        vertical = (torch.minimum(yy + 1/h, torch.tensor(bottom)) - torch.maximum(yy, torch.tensor(top))).clamp_min(0) * h
        masks.append(vertical[:, None] * horizontal[None, :])
    return torch.stack(masks)


def moss_layout_prompt(pipe, width, height):
    if not all(c.bbox is not None for c in pipe.regions):
        raise ValueError("MOSS native layout needs boxes for every region. Choose boxes, or use regional for mixed point/box layouts. / 좌표와 상자를 함께 쓰려면 regional을 선택해 주세요. MOSS 공식 모드는 모든 영역에 상자가 필요합니다.")
    items = []
    from .characters import TextRegion
    for c in pipe.regions:
        left, top, right, bottom = c.bbox
        box = [math.floor(round(top*height, 9))-height//2,
               math.floor(round(left*width, 9))-width//2,
               math.ceil(round(bottom*height, 9))-height//2,
               math.ceil(round(right*width, 9))-width//2]
        if box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError("A MOSS box is smaller than one pixel. Increase its size.")
        item = {"label": "text" if isinstance(c, TextRegion) else "object", "caption": c.prompt, "bbox": box}
        if isinstance(c, TextRegion):
            item["text"] = c.text
        items.append(item)
    return json.dumps({"summary": {"canvas": "single", "caption": pipe.prompt or ""},
        "items": items, "bbox_coord_space": "abs_centralized", "bbox_format": "yxyx"},
        ensure_ascii=False, allow_nan=False)
