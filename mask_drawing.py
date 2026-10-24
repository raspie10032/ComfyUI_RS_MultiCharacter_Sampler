# SPDX-License-Identifier: GPL-3.0-only
"""Painted character layers. The reference image never becomes model input."""
import json
import math

import numpy as np
from PIL import Image, ImageDraw
import torch

from .character_builder import BUILD_PIPE_TYPE, update_slot
from .region_mask import prepare_mask, validate_mask_budget

EMPTY_DRAWING = '{"version":1,"width":768,"height":1024,"layers":{}}'
MAX_POINTS = 100000


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid mask drawing value. / 마스크의 수치·크기를 확인해 주세요. / マスクの数値・サイズを確認してください。")
    return value


def read_drawing(drawing):
    if not isinstance(drawing, str) or len(drawing) > 4 * 1024 * 1024:
        raise ValueError("Drawing is too large. Simplify the strokes. / 획이 너무 많습니다. 단순하게 다시 그려 주세요. / 線が多すぎます。簡略化してください。")
    try:
        data = json.loads(drawing)
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
            raise ValueError("Unsupported mask drawing version.")
        for key in ("width", "height"):
            if type(data.get(key)) is not int or not 64 <= data[key] <= 2048:
                raise ValueError("Drawing canvas must be 64–2048 pixels per side.")
        layers = data["layers"]
        if not isinstance(layers, dict) or len(layers) > 10:
            raise ValueError("Use up to ten drawing layers.")
        count = 0
        for key, layer in layers.items():
            if key not in {str(i) for i in range(1, 11)} or not isinstance(layer, dict):
                raise ValueError("Drawing layers must use character numbers 1–10.")
            for name, default, low, high in (("scale", 1, .05, 4), ("x", 0, -1, 1), ("y", 0, -1, 1)):
                number(layer.get(name, default), low, high)
            strokes = layer["strokes"]
            if not isinstance(strokes, list) or len(strokes) > 2000:
                raise ValueError("Too many drawing strokes.")
            for stroke in strokes:
                if not isinstance(stroke, dict) or stroke.get("tool") not in ("brush", "erase"):
                    raise ValueError("Choose brush or eraser.")
                number(stroke["size"], .001, .5)
                points = stroke["points"]
                if not isinstance(points, list) or not points:
                    raise ValueError("Drawing strokes need points.")
                count += len(points)
                if count > MAX_POINTS:
                    raise ValueError("Too many drawing points. Simplify the drawing.")
                for point in points:
                    if not isinstance(point, list) or len(point) != 2:
                        raise ValueError("Invalid drawing point.")
                    # Permit a captured pointer to leave the canvas; rasterizing
                    # clips rather than wrapping or moving the stroke inside.
                    for coordinate in point:
                        number(coordinate, -4, 5)
        return data
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid mask drawing. Reopen the drawing node and check the layers. / 마스크 드로잉 데이터를 확인해 주세요. / マスク描画データを確認してください。") from error


def raster_layer(data, layer):
    w, h = data["width"], data["height"]
    image = Image.new("L", (w, h))
    draw = ImageDraw.Draw(image)
    for stroke in layer["strokes"]:
        points = [(x * w, y * h) for x, y in stroke["points"]]
        width = max(1, round(stroke["size"] * min(w, h)))
        fill = 0 if stroke["tool"] == "erase" else 255
        if len(points) > 1:
            draw.line(points, fill=fill, width=width, joint="curve")
        radius = width / 2
        for x, y in points:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill)
    return torch.from_numpy(np.array(image, dtype=np.float32) / 255)


class RSMultiCharacterMaskDraw:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "drawing": ("STRING", {"default": EMPTY_DRAWING, "multiline": False,
                "tooltip": "Paint numbered layers over a reference image. Only the masks enter generation."}),
            "margin": ("INT", {"default": 24, "min": 0, "max": 128,
                "tooltip": "Extra space around painted layers, in drawing-canvas pixels."}),
        }, "optional": {"building_pipe": (BUILD_PIPE_TYPE,)}}

    RETURN_TYPES = (BUILD_PIPE_TYPE,)
    RETURN_NAMES = ("building_pipe",)
    FUNCTION = "apply"
    CATEGORY = "RS MultiCharacter/Characters"
    DESCRIPTION = "Paint up to ten numbered character masks over a reference image. Numbers match Prompt/LoRA. The image is a guide only, never img2img input. This node replaces the mask table; blank layers use XY/boxes. Move/scale each layer; overflow is clipped. Approximate layout, not pose control."

    def apply(self, drawing=EMPTY_DRAWING, margin=24, building_pipe=None):
        data = read_drawing(drawing)
        if type(margin) is not int or not 0 <= margin <= 128:
            raise ValueError("Drawing margin must be 0–128 pixels.")
        pipe = building_pipe
        populated = False
        for i in range(1, 11):
            region = None
            layer = data["layers"].get(str(i))
            if layer and layer["strokes"]:
                raster = raster_layer(data, layer)
                if raster.any():
                    region = prepare_mask(raster, margin=margin, offset_x=layer.get("x", 0),
                                          offset_y=layer.get("y", 0), scale=layer.get("scale", 1))
                    populated = True
            # The painted table replaces pose-derived masks as well. Keeping
            # their part labels would guide the old pose under the new drawing.
            pipe = update_slot(pipe, i, region_mask=region, body_parts=(), body_part_strength=0.)
        if not populated:
            raise ValueError("Paint at least one character region. / 캐릭터 번호를 선택하고 영역을 칠해 주세요. / キャラクター番号を選んで領域を塗ってください。")
        validate_mask_budget(pipe.slots)
        return (pipe,)
