# SPDX-License-Identifier: GPL-3.0-only
"""Original prompt text travels in one dedicated, immutable pipe."""
from dataclasses import dataclass, field
import math
from .region_mask import RegionMask, validate_mask_budget

PIPE_TYPE = "RS_MC_CHARACTER_PIPE"
LORA_MODES = ["normal", "precision"]


def validate_lora_mode(mode):
    if mode not in LORA_MODES:
        raise ValueError("Choose normal or precision for LoRA application. / LoRA 적용 모드는 일반 또는 정밀을 선택해 주세요. / LoRA適用は通常または精密を選んでください。")


@dataclass(frozen=True)
class Character:
    prompt: str
    uc: str = ""
    x: float = .5
    y: float = .5
    # Normalized left, top, right, bottom; absent in pre-Epsilon pipes.
    bbox: tuple | None = None
    lora_name: str = field(default="None", kw_only=True)
    lora_strength: float = field(default=1., kw_only=True)
    lora_clip_strength: float = field(default=1., kw_only=True)
    region_mask: RegionMask | None = field(default=None, kw_only=True)

    def __post_init__(self):
        if self.region_mask is not None and not isinstance(self.region_mask, RegionMask):
            raise ValueError("Invalid character region mask.")
        if not isinstance(self.prompt, str) or not isinstance(self.uc, str):
            raise ValueError("Character prompts must be text.")
        if not isinstance(self.lora_name, str) or not self.lora_name:
            raise ValueError("Choose a local LoRA file or None.")
        for value in (self.lora_strength, self.lora_clip_strength):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("LoRA strengths must be finite numbers.")
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or
               not math.isfinite(v) or not 0 <= v <= 1 for v in (self.x, self.y)):
            raise ValueError("Character X/Y must be finite numbers from 0 to 1.")
        if self.bbox is not None:
            if (not isinstance(self.bbox, tuple) or len(self.bbox) != 4 or
                    any(isinstance(v, bool) or not isinstance(v, (float, int)) or
                        not math.isfinite(v) or not 0 <= v <= 1 for v in self.bbox)):
                raise ValueError("A character box needs four finite coordinates in [0, 1].")
            left, top, right, bottom = self.bbox
            if left >= right or top >= bottom:
                raise ValueError("A character box must have positive width and height.")
            if not (math.isclose(self.x, (left + right) / 2, abs_tol=1e-9) and
                    math.isclose(self.y, (top + bottom) / 2, abs_tol=1e-9)):
                raise ValueError("Character X/Y must match the box center.")

    @property
    def center(self):
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class TextRegion(Character):
    text: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.region_mask is not None:
            raise ValueError("Text uses a box, not a character mask. / 글자 영역에는 마스크 대신 상자를 사용해 주세요. / 文字領域にはボックスを使ってください。")
        if self.bbox is None or not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("A text region needs a box and nonempty literal text. / 텍스트 영역에는 상자와 실제로 쓸 글자를 입력해 주세요.")
        if self.lora_name != "None":
            raise ValueError("Per-character LoRA is not applied to text regions.")


@dataclass(frozen=True)
class CharacterPipe:
    characters: tuple
    prompt: str | None = None
    negative_prompt: str | None = None
    syntax: str = "ComfyUI"
    # Serialized snapshot avoids shared mutable state between consumers.
    generation_json: str | None = None
    # Text regions never enter character matching or NAI character captions.
    text_regions: tuple = ()
    lora_application_mode: str = field(default="precision", kw_only=True)

    @property
    def regions(self):
        return self.characters + self.text_regions

    def __post_init__(self):
        validate_lora_mode(self.lora_application_mode)
        if not isinstance(self.characters, tuple) or not isinstance(self.text_regions, tuple) or not 1 <= len(self.regions) <= 10:
            raise ValueError("Use 1–10 active regions in total. / 활성 캐릭터와 텍스트 영역을 합쳐 1~10개 입력해 주세요.")
        if any(type(c) is not Character or not c.prompt.strip() for c in self.characters):
            raise ValueError("Every active character needs a nonempty prompt.")
        if any(not isinstance(c, TextRegion) or not c.prompt.strip() for c in self.text_regions):
            raise ValueError("Every text region needs a style description and literal text.")
        if any(c.region_mask is not None for c in self.characters):
            validate_mask_budget(self.characters)
        if self.syntax not in ("ComfyUI", "NovelAI"):
            raise ValueError("Unsupported prompt syntax.")
        if any(v is not None and not isinstance(v, str) for v in (self.prompt, self.negative_prompt, self.generation_json)):
            raise ValueError("Invalid character pipe text.")


class RSMultiCharacterPrompts:
    # Load old workflows without changing positional widget serialization.
    DEPRECATED = True
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        fields = {"character_count": ("INT", {"default": 5, "min": 1, "max": 10,
            "tooltip": "Only visible, enabled, nonempty slots are used. Hidden text stays saved but is not generated."})}
        for i in range(1, 11):
            fields.update({
                f"character{i}_enable": ("BOOLEAN", {"default": True}),
                f"character{i}": ("STRING", {"default": "", "multiline": True}),
                f"character{i}_uc": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "Reserved for metadata round trips. Regional sampling supports a common negative only; nonempty character negatives give an explicit error."}),
                f"character{i}_x": ("FLOAT", {"default": .5, "min": 0., "max": 1., "step": .05}),
                f"character{i}_y": ("FLOAT", {"default": .5, "min": 0., "max": 1., "step": .05}),
            })
        # Append optional widgets: positional values in older workflows stay put.
        boxes = {"layout_mode": (["points", "boxes", "mixed"], {"default": "points",
            "tooltip": "Points divide the full canvas. Boxes use center X/Y and width/height. Mixed lets each slot use points or a box; boxes take priority over point regions. Text always uses a box. Outside all regions uses the common prompt; overlapping boxes share their captions."})}
        for i in range(1, 11):
            for axis, default in (("width", .4), ("height", .8)):
                boxes[f"character{i}_{axis}"] = ("FLOAT", {"default": default, "min": .01, "max": 1., "step": .01})
        for i in range(1, 11):
            boxes[f"character{i}_kind"] = (["character", "text"], {"default": "character",
                "tooltip": "Boxes/mixed modes. Text uses this slot's prompt for font/color/style and its literal-text field for the word to draw. Text regions do not count as people in the detailer."})
            boxes[f"character{i}_text"] = ("STRING", {"default": "", "multiline": True,
                "tooltip": "Exact visible text, e.g. HELLO. Model spelling and placement are not guaranteed. Remove 'text' from the common negative prompt when requesting text."})
        for i in range(1, 11):
            boxes[f"character{i}_geometry"] = (["point", "box"], {"default": "point",
                "tooltip": "Mixed mode: point = automatic partition from X/Y; box = explicit center and size. Text always uses a box. Boxes take priority inside their bounds."})
        for i in range(1, 11):
            boxes[f"character{i}_lora"] = (["None", *folder_paths.get_filename_list("loras")], {"default": "None",
                "tooltip": "Optional LoRA for this character. Use a file for the connected model family. Separate LoRA predictions are blended in this region; more distinct LoRAs increase time and memory. Global style/acceleration LoRAs still use normal loaders."})
            boxes[f"character{i}_lora_strength"] = ("FLOAT", {"default": 1., "min": -10., "max": 10., "step": .05,
                "tooltip": "Diffusion-model LoRA strength in this region. Zero disables the model part."})
            boxes[f"character{i}_lora_clip_strength"] = ("FLOAT", {"default": 1., "min": -10., "max": 10., "step": .05,
                "tooltip": "Text-encoder LoRA strength for this character's prompt only, if the file contains compatible text-encoder weights. Zero disables that part."})
        return {"required": fields, "optional": boxes}

    RETURN_TYPES = (PIPE_TYPE,)
    RETURN_NAMES = ("character_pipe",)
    FUNCTION = "build"
    CATEGORY = "RS MultiCharacter"
    DESCRIPTION = "1–10 character/text regions with X/Y points, boxes, or both. Coincident points spread left to right. In mixed mode boxes take priority over point regions. Text uses a literal word and style description in a box; spelling depends on the model. More characters do not guarantee quality. / 처리수가 많을수록 품질을 보장하지 못합니다."

    def build(self, character_count=5, layout_mode="points", **values):
        if layout_mode not in ("points", "boxes", "mixed"):
            raise ValueError("Choose points, boxes, or mixed for the layout.")
        if type(character_count) is not int or not 1 <= character_count <= 10:
            raise ValueError("Choose 1–10 character slots.")
        chars, text_regions = [], []
        for i in range(1, character_count + 1):
            if not values.get(f"character{i}_enable", True):
                continue
            text = values.get(f"character{i}", "")
            if not isinstance(text, str):
                raise ValueError(f"Character {i} prompt must be text.")
            kind = values.get(f"character{i}_kind", "character")
            if kind not in ("character", "text"):
                raise ValueError(f"Slot {i}: choose character or text.")
            if layout_mode == "points" and kind == "text":
                continue
            if kind == "text" and not text.strip():
                text = "Clear legible lettering"
            if text.strip():
                geometry = values.get(f"character{i}_geometry", "point") if layout_mode == "mixed" else "point"
                if geometry not in ("point", "box"):
                    raise ValueError(f"Slot {i}: choose point or box geometry.")
                x, y = values.get(f"character{i}_x", .5), values.get(f"character{i}_y", .5)
                bbox = None
                if layout_mode == "boxes" or (layout_mode == "mixed" and (kind == "text" or geometry == "box")):
                    width, height = values.get(f"character{i}_width", .4), values.get(f"character{i}_height", .8)
                    for value in (x, y, width, height):
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                            raise ValueError(f"Character {i}: use finite numeric box coordinates.")
                    if not 0 < width <= 1 or not 0 < height <= 1:
                        raise ValueError(f"Character {i}: box width/height must be greater than 0 and at most 1.")
                    bbox = (x - width/2, y - height/2, x + width/2, y + height/2)
                    if any(v < -1e-9 or v > 1+1e-9 for v in bbox):
                        raise ValueError(f"Character {i}: the box extends outside the image. Move X/Y inward or reduce width/height. / 캐릭터 {i}: 상자가 화면 밖으로 나갑니다. 중심을 안쪽으로 옮기거나 크기를 줄여 주세요.")
                    bbox = tuple(min(1., max(0., v)) for v in bbox)
                if kind == "text":
                    text_regions.append(TextRegion(text, values.get(f"character{i}_uc", ""), x, y, bbox,
                        values.get(f"character{i}_text", "")))
                else:
                    chars.append(Character(text, values.get(f"character{i}_uc", ""), x, y, bbox,
                        lora_name=values.get(f"character{i}_lora", "None"),
                        lora_strength=values.get(f"character{i}_lora_strength", 1.),
                        lora_clip_strength=values.get(f"character{i}_lora_clip_strength", 1.)))
        return (CharacterPipe(tuple(chars), text_regions=tuple(text_regions)),)
