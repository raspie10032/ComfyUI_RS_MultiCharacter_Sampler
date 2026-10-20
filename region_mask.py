# SPDX-License-Identifier: GPL-3.0-only
"""Immutable, bounded binary prompt regions; never pose or noise conditioning."""
import base64
from dataclasses import dataclass
import hashlib
import json
import math
import zlib

import numpy as np
import torch
import torch.nn.functional as F

MAX_SIDE = 4096


@dataclass(frozen=True)
class RegionMask:
    width: int
    height: int
    packed: bytes

    def __post_init__(self):
        if (type(self.width) is not int or type(self.height) is not int or
                not 1 <= self.width <= MAX_SIDE or not 1 <= self.height <= MAX_SIDE):
            raise ValueError("Region mask dimensions must be 1–4096 pixels.")
        if type(self.packed) is not bytes or len(self.packed) != (self.width*self.height+7)//8:
            raise ValueError("Invalid region mask payload size.")
        if not any(self.packed):
            raise ValueError("The region mask is empty. Paint white where this character belongs. / 영역 마스크가 비었습니다. 캐릭터 영역을 흰색으로 칠해 주세요. / キャラクター領域を白で塗ってください。")
        remainder = self.width*self.height % 8
        if remainder and self.packed[-1] & ((1 << (8-remainder))-1):
            raise ValueError("Invalid region mask padding bits.")

    def tensor(self):
        bits = np.unpackbits(np.frombuffer(self.packed, dtype=np.uint8), count=self.width*self.height)
        return torch.from_numpy(bits.reshape(self.height, self.width).astype(np.float32))

    def record(self):
        return {"encoding": "bitpack-zlib-v1", "width": self.width, "height": self.height,
                "data": base64.b64encode(zlib.compress(self.packed)).decode("ascii"),
                "sha256": hashlib.sha256(self.packed).hexdigest()}

    @property
    def center(self):
        mask = self.tensor()
        total = mask.sum()
        return (float((mask.sum(0)*(torch.arange(self.width)+.5)).sum()/total/self.width),
                float((mask.sum(1)*(torch.arange(self.height)+.5)).sum()/total/self.height))

    @classmethod
    def from_record(cls, value):
        try:
            if not isinstance(value, dict) or value.get("encoding") != "bitpack-zlib-v1":
                raise ValueError("Unsupported region mask encoding.")
            w, h = value["width"], value["height"]
            if type(w) is not int or type(h) is not int or not 1 <= w <= MAX_SIDE or not 1 <= h <= MAX_SIDE:
                raise ValueError("Invalid region mask dimensions.")
            data = value["data"]
            if not isinstance(data, str) or len(data) > 3*1024*1024:
                raise ValueError("Region mask data is too large.")
            stream = zlib.decompressobj()
            size = (w*h+7)//8
            packed = stream.decompress(base64.b64decode(data, validate=True), size+1)
            if len(packed) != size or not stream.eof or stream.unused_data or stream.unconsumed_tail:
                raise ValueError("Invalid compressed region mask size.")
            if hashlib.sha256(packed).hexdigest() != value["sha256"]:
                raise ValueError("Region mask checksum differs.")
            return cls(w, h, packed)
        except (KeyError, TypeError, zlib.error) as error:
            raise ValueError("Invalid region mask metadata.") from error


def prepare_mask(mask, threshold=.5, margin=24, offset_x=0., offset_y=0., scale=1., *, pivot=(.5, .5)):
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or
            not math.isfinite(threshold) or not 0 <= threshold <= 1):
        raise ValueError("Mask threshold must be 0–1.")
    if type(margin) is not int or not 0 <= margin <= 128:
        raise ValueError("Mask margin must be 0–128 source pixels.")
    for name, value, lower, upper in (("offset_x", offset_x, -1, 1),
                                      ("offset_y", offset_y, -1, 1),
                                      ("scale", scale, .05, 4)):
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value) or not lower <= value <= upper):
            raise ValueError(f"Mask {name} must be {lower}–{upper}.")
    if not isinstance(mask, torch.Tensor) or mask.ndim not in (2, 3):
        raise ValueError("Connect a MASK: white selects the character region. / 흰색 영역을 지정한 MASK를 연결해 주세요. / MASKを接続してください。")
    if mask.ndim == 3:
        if mask.shape[0] != 1:
            raise ValueError("Use one mask per character, not a mask batch. / 캐릭터마다 마스크 한 장을 연결해 주세요. / 1人につき1枚のマスクを接続してください。")
        mask = mask[0]
    h, w = mask.shape
    if not 1 <= w <= MAX_SIDE or not 1 <= h <= MAX_SIDE:
        raise ValueError("Use a mask up to 4096×4096 pixels.")
    mask = mask.detach().to(device="cpu", dtype=torch.float32)
    if not torch.isfinite(mask).all() or (mask < 0).any() or (mask > 1).any():
        raise ValueError("Mask pixels must be finite values from 0 to 1.")
    mask = (mask > threshold).float()
    if offset_x != 0 or offset_y != 0 or scale != 1:
        # Inverse nearest-neighbour mapping about the full source-canvas centre.
        # Keep the canvas fixed: no wrap, fit-to-bounds or allocation at scale*w.
        x = torch.floor((torch.arange(w, dtype=torch.float64)+.5-pivot[0]*w-offset_x*w)/scale+pivot[0]*w).long()
        y = torch.floor((torch.arange(h, dtype=torch.float64)+.5-pivot[1]*h-offset_y*h)/scale+pivot[1]*h).long()
        inside = ((y >= 0) & (y < h))[:, None] & ((x >= 0) & (x < w))[None, :]
        mask = mask[y.clamp(0, h-1)[:, None], x.clamp(0, w-1)[None, :]] * inside
        if not mask.any():
            raise ValueError("The mask is outside the canvas or too small. Reduce the offset or increase its size. / 마스크가 캔버스 밖에 있거나 너무 작습니다. 이동을 줄이거나 크기를 늘려 주세요. / マスクがキャンバス外か小さすぎます。移動を戻すか拡大してください。")
    if margin:
        # Separable square dilation avoids a large 2-D pooling kernel.
        mask = F.max_pool2d(mask[None, None], (1, 2*margin+1), stride=1, padding=(0, margin))
        mask = F.max_pool2d(mask, (2*margin+1, 1), stride=1, padding=(margin, 0))[0, 0]
    packed = np.packbits(mask.numpy().astype(np.uint8).reshape(-1)).tobytes()
    return RegionMask(w, h, packed)


def place_mask(mask, transform):
    """Non-destructive Position edit, about the source mask's own centroid."""
    dx, dy, scale = transform
    if (dx, dy, scale) == (0., 0., 1.):
        return mask
    return prepare_mask(mask.tensor(), margin=0, offset_x=dx, offset_y=dy,
                        scale=scale, pivot=mask.center)


def mask_records(pipe):
    return [c.region_mask.record() if c.region_mask is not None else None for c in pipe.characters]


def validate_mask_budget(characters):
    # Reserve room for captions/settings inside the 4 MiB image metadata limit.
    records = [c.region_mask.record() if c.region_mask is not None else None for c in characters]
    if len(json.dumps(records)) > 3*1024*1024:
        raise ValueError("Character masks exceed the metadata budget. Reduce mask resolution or simplify the masks. / 마스크 해상도나 복잡도를 줄여 주세요. / マスクの解像度を下げてください。")


def explicit_region(c):
    return c.bbox is not None or c.region_mask is not None
