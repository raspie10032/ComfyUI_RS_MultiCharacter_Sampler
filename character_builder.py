# SPDX-License-Identifier: GPL-3.0-only
"""Order-independent, immutable editing of numbered character slots."""
from dataclasses import dataclass, field, replace

from .characters import Character, CharacterPipe, TextRegion, PIPE_TYPE, LORA_MODES, validate_lora_mode
from .region_mask import RegionMask, prepare_mask, place_mask

import json
import math

BUILD_PIPE_TYPE = "RS_MC_BUILD_PIPE"


@dataclass(frozen=True)
class Slot:
    number: int
    prompt: str | None = None
    enabled: bool = True
    kind: str = "character"
    literal_text: str = ""
    geometry: str = "point"
    x: float = .5
    y: float = .5
    width: float = .4
    height: float = .8
    lora_name: str = "None"
    strength_model: float = 1.
    strength_clip: float = 1.
    region_mask: RegionMask | None = None
    mask_transform: tuple = (0., 0., 1.)
    body_parts: tuple = ()
    body_part_strength: float = 0.
    reference: object = field(default=None, repr=False, compare=False)
    uc: str = ""


@dataclass(frozen=True)
class BuildPipe:
    slots: tuple = ()
    prompt_count: int | None = None
    lora_application_mode: str = "precision"
    interaction_json: str | None = None
    source_pipe: CharacterPipe | None = field(default=None, repr=False)
    camera_settings: tuple = ()
    pose3d_masks: tuple = ()
    pose3d_json: str | None = None

    def rs_defer_camera(self, options):
        """A global view applies after slot assembly, independent of role order."""
        return replace(self, camera_settings=(tuple(options.items()),))

    def rs_camera_preview(self):
        from .camera_layout import layout_preview
        try:
            return layout_preview(finalize(self, apply_cameras=False))
        except ValueError:
            return []  # An unfinished builder need not have its prompts yet.


def update_slot(pipe, character_id, **changes):
    if type(character_id) is not int or not 1 <= character_id <= 10:
        raise ValueError("Choose character number 1–10. / 캐릭터 번호는 1~10입니다. / キャラクター番号は1～10です。")
    if pipe is None:
        pipe = BuildPipe()
    if not isinstance(pipe, BuildPipe):
        raise ValueError("Connect the building pipe from Prompt, LoRA or Position. / 프롬프트·LoRA·위치의 조립 파이프를 연결해 주세요. / 組み立てパイプを接続してください。")
    slots = {s.number: s for s in pipe.slots}
    slots[character_id] = replace(slots.get(character_id, Slot(character_id)), **changes)
    return replace(pipe, slots=tuple(slots[n] for n in sorted(slots)))


def slot_box(slot):
    if slot.geometry == "point":
        return None
    import math
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (slot.width, slot.height)) or not (0 < slot.width <= 1 and 0 < slot.height <= 1):
        raise ValueError("Box width/height must be in (0, 1]. / 상자 크기는 0 초과 1 이하입니다. / ボックスのサイズは0より大きく1以下です。")
    box = (slot.x-slot.width/2, slot.y-slot.height/2, slot.x+slot.width/2, slot.y+slot.height/2)
    if any(v < -1e-9 or v > 1+1e-9 for v in box):
        raise ValueError(f"Character {slot.number}: box outside image; move its center inward or reduce its size. / 캐릭터 {slot.number}: 상자가 화면 밖입니다. 중심이나 크기를 조정해 주세요. / ボックスが画像の範囲外です。")
    return tuple(min(1., max(0., v)) for v in box)


def finalize(pipe, *, apply_cameras=True):
    if not isinstance(pipe, BuildPipe):
        raise ValueError("Connect a building pipe first. / 조립 파이프를 연결해 주세요. / 組み立てパイプを接続してください。")
    if pipe.prompt_count is None:
        raise ValueError("Connect a Character Prompts node anywhere before Finalize. / 최종 파이프 앞에 캐릭터 프롬프트 노드를 연결해 주세요. / プロンプトノードを接続してください。")
    from .pipe_compat import building_pipe
    source = pipe.source_pipe
    source_slots = {s.number: s for s in building_pipe(source).slots} if source is not None else {}
    chars, texts = [], []
    for s in pipe.slots:
        if s.number > pipe.prompt_count or not s.enabled:
            continue
        original = source_slots.get(s.number)
        if original is not None and s == original and s.reference is original.reference:
            region = source.regions[s.number-1]
            (texts if isinstance(region, TextRegion) else chars).append(region)
            continue
        if s.prompt is None or not s.prompt.strip():
            raise ValueError(f"Character {s.number}: connect a nonempty STRING to the matching Prompt row, or disable that row. / 캐릭터 {s.number}: 프롬프트 노드의 해당 번호에 STRING을 연결하거나 그 행의 사용을 꺼 주세요. / 同じ番号のプロンプトに文字列を接続するか無効にしてください。")
        Character(s.prompt, x=s.x, y=s.y, lora_name=s.lora_name,
                  lora_strength=s.strength_model, lora_clip_strength=s.strength_clip)
        box = slot_box(s) if s.region_mask is None else None
        if s.kind == "text":
            if s.reference is not None and s.reference.strength > 0:
                raise ValueError("Image references apply to character slots only. / 이미지 참조는 캐릭터 슬롯에만 적용됩니다. / 画像参照はキャラクター専用です。")
            if s.region_mask is not None:
                raise ValueError(f"Slot {s.number}: text uses a box; disable its Character Mask. / 글자 슬롯의 캐릭터 마스크를 꺼 주세요. / 文字スロットのマスクを無効にしてください。")
            if s.geometry != "box":
                raise ValueError(f"Character {s.number}: text needs a Position node in box mode. / 글자 영역은 위치 노드를 상자로 설정해 주세요. / 文字領域にはボックス位置が必要です。")
            if s.lora_name != "None":
                raise ValueError(f"Character {s.number}: text regions do not use character LoRAs; choose None. / 글자 영역의 LoRA는 None으로 설정해 주세요. / 文字領域のLoRAはNoneにしてください。")
            texts.append(TextRegion(s.prompt, s.uc, s.x, s.y, box, s.literal_text))
        else:
            region = place_mask(s.region_mask, s.mask_transform) if s.region_mask is not None else None
            x, y = region.center if region is not None else (s.x, s.y)
            chars.append(Character(s.prompt, s.uc, x, y, box, lora_name=s.lora_name,
                                   lora_strength=s.strength_model, lora_clip_strength=s.strength_clip,
                                   region_mask=region, reference=s.reference,
                                   body_parts=placed_parts(s), body_part_strength=s.body_part_strength))
    if not chars and not texts:
        raise ValueError("Enable at least one nonempty prompt. / 최소 한 개의 프롬프트를 켜 주세요. / 少なくとも1つのプロンプトを有効にしてください。")
    if source is not None:
        result = replace(source, characters=tuple(chars), text_regions=tuple(texts),
                       lora_application_mode=pipe.lora_application_mode, interaction_json=pipe.interaction_json)
    else:
        result = CharacterPipe(tuple(chars), text_regions=tuple(texts), lora_application_mode=pipe.lora_application_mode,
                               interaction_json=pipe.interaction_json)
    result = replace(result, pose3d_json=pipe.pose3d_json if pipe.pose3d_json is not None else
                     source.pose3d_json if source is not None else None)
    if apply_cameras and pipe.camera_settings:
        from .camera_control import RSCameraControl
        for options in pipe.camera_settings:
            result = RSCameraControl().apply(building_pipe=result, **dict(options))["result"][0]
    return result


def placed_parts(slot):
    """Move every part about the PERSON centroid, never its own centroid."""
    if not slot.body_parts:
        return ()
    if slot.region_mask is None:
        return ()
    dx, dy, scale = slot.mask_transform
    if (dx, dy, scale) == (0., 0., 1.):
        return slot.body_parts
    parts = []
    for name, mask in slot.body_parts:
        try:
            region = prepare_mask(mask.tensor(), margin=0, offset_x=dx, offset_y=dy,
                                  scale=scale, pivot=slot.region_mask.center)
        except ValueError as error:
            if 'mask is empty' not in str(error) and 'mask is outside the canvas' not in str(error):
                raise
            continue  # A partially clipped person may have a completely clipped hand.
        parts.append((name, region))
    return tuple(parts)


def count_input():
    return ("INT", {"default": 2, "min": 1, "max": 10,
        "tooltip": "Show all slots 1–N together. Prompt count determines the active regions; LoRA/Position counts determine which settings they supply. / 1~N번 설정을 함께 표시합니다. 최종 인원수는 프롬프트 노드 기준입니다."})


ROLE_FIELDS = {
    "prompt": ("prompt", "enabled", "kind", "literal_text"),
    "lora": ("lora_name", "strength_model", "strength_clip"),
    "position": ("geometry", "x", "y", "width", "height", "mask_transform"),
}


def read_mask_transforms(value):
    """Position-only offsets; source masks remain independent of builder order."""
    try:
        if not isinstance(value, str) or len(value) > 8192:
            raise ValueError()
        data = json.loads(value)
        if not isinstance(data, dict) or len(data) > 10:
            raise ValueError()
        result = {}
        for key, transform in data.items():
            if key not in {str(i) for i in range(1, 11)} or not isinstance(transform, list) or len(transform) != 3:
                raise ValueError()
            for v, low, high in zip(transform, (-1, -1, .05), (1, 1, 4)):
                if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
                    raise ValueError()
            result[int(key)] = tuple(transform)
        return result
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid mask placement. Reset that mask's placement in Position. / 마스크 배치값이 잘못되었습니다. 위치 노드에서 배치를 초기화해 주세요. / Positionでマスク配置をリセットしてください。") from error


def apply_role(pipe, role, count, settings):
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError("Choose 1–10 slots. / 개수는 1~10입니다. / 1～10を選んでください。")
    # Replace only this role's table. This also clears stale hidden values when
    # the same role is repeated with fewer rows, without mutating a shared pipe.
    for i in range(1, 11):
        defaults = Slot(i)
        changes = {key: getattr(defaults, key) for key in ROLE_FIELDS[role]}
        if i <= count:
            changes.update(settings(i))
        pipe = update_slot(pipe, i, **changes)
    return replace(pipe, prompt_count=count) if role == "prompt" else pipe


class BuilderNode:
    RETURN_TYPES = (BUILD_PIPE_TYPE,)
    RETURN_NAMES = ("building_pipe",)
    FUNCTION = "apply"
    CATEGORY = "RS MultiCharacter/Characters"


class RSMultiCharacterPrompt(BuilderNode):
    @classmethod
    def INPUT_TYPES(cls):
        required = {"character_count": count_input()}
        optional = {"building_pipe": (BUILD_PIPE_TYPE,)}
        for i in range(1, 11):
            required[f"character{i}_enable"] = ("BOOLEAN", {"default": True})
            required[f"character{i}_kind"] = (["character", "text"], {"default": "character"})
            optional[f"character{i}"] = ("STRING", {"forceInput": True, "tooltip": f"Slot {i}: character = positive prompt; text = exact words to draw. The same connection is kept when switching kind. Text needs a box Position."})
            # Accept previous API workflows. The UI migrates this connection to
            # character{i}; new workflows use one STRING regardless of kind.
            optional[f"character{i}_text"] = ("STRING", {"forceInput": True, "tooltip": "Legacy literal-text connection; migrated to the shared STRING input."})
        return {"required": required, "optional": optional}

    DESCRIPTION = "One STRING per slot: character uses it as a positive prompt, text uses it as the words to draw. Switching kind keeps the connection. No per-character UC. This node sets the active count; hidden slots are excluded even if connected. LoRA and Position may be connected in any order."

    def apply(self, character_count=2, building_pipe=None, **values):
        def settings(i):
            enabled = values.get(f"character{i}_enable", True)
            kind = values.get(f"character{i}_kind", "character")
            prompt, literal = values.get(f"character{i}", ""), values.get(f"character{i}_text", "")
            if type(enabled) is not bool or kind not in ("character", "text"):
                raise ValueError(f"Character {i}: choose character/text and enable/disable.")
            if not isinstance(prompt, str) or not isinstance(literal, str):
                raise ValueError(f"Character {i}: connect STRING text.")
            if kind == "text":
                if literal.strip():
                    # Old API workflows supplied both a style and literal text.
                    prompt = prompt if prompt.strip() else "Clear legible lettering"
                else:
                    literal, prompt = prompt, "Clear legible lettering"
            else:
                literal = ""
            return dict(prompt=prompt, enabled=enabled, kind=kind, literal_text=literal)
        return (apply_role(building_pipe, "prompt", character_count, settings),)


class RSMultiCharacterLoRA(BuilderNode):
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        fields = {"character_count": count_input()}
        files = ["None", *folder_paths.get_filename_list("loras")]
        for i in range(1, 11):
            fields[f"character{i}_lora"] = (files, {"default": "None"})
            fields[f"character{i}_lora_strength"] = ("FLOAT", {"default": 1., "min": -10., "max": 10., "step": .05})
            fields[f"character{i}_lora_clip_strength"] = ("FLOAT", {"default": 1., "min": -10., "max": 10., "step": .05})
        return {"required": fields, "optional": {"building_pipe": (BUILD_PIPE_TYPE,),
            "lora_application_mode": (LORA_MODES, {"default": "precision",
                "tooltip": "Normal shares layer calculations for supported Anima/SDXL linear LoRAs. Precision keeps independent predictions per LoRA setting with low-rank optimization. Precision is the compatibility default, not a quality guarantee. Unsupported normal mode uses precision and reports why. Applies to all slots in this pipe; the sampler reads it automatically. Detailing samples one matched character at a time using precision in both modes."})}}

    DESCRIPTION = "View and set all character LoRAs together. Numbers match the prompt table. Unlisted slots use None. Models load at generation/detailing; use files for the connected model family."

    def apply(self, character_count=2, building_pipe=None, lora_application_mode="precision", **values):
        validate_lora_mode(lora_application_mode)
        pipe = apply_role(building_pipe, "lora", character_count, lambda i: dict(
            lora_name=values.get(f"character{i}_lora", "None"),
            strength_model=values.get(f"character{i}_lora_strength", 1.),
            strength_clip=values.get(f"character{i}_lora_clip_strength", 1.)))
        return (replace(pipe, lora_application_mode=lora_application_mode),)


class RSMultiCharacterPosition(BuilderNode):
    @classmethod
    def INPUT_TYPES(cls):
        fields = {"character_count": count_input()}
        for i in range(1, 11):
            fields[f"character{i}_geometry"] = (["point", "box"], {"default": "point"})
            for key, default in (("x", .5), ("y", .5), ("width", .4), ("height", .8)):
                fields[f"character{i}_{key}"] = ("FLOAT", {"default": default, "min": .01 if key in ("width", "height") else 0., "max": 1., "step": .01})
        return {"required": fields, "optional": {"building_pipe": (BUILD_PIPE_TYPE,),
            "mask_transforms": ("STRING", {"default": "{}", "multiline": False,
                "tooltip": "Saved mask offsets and uniform scale from the layout editor. Use the selector above the canvas to edit."})}}

    DESCRIPTION = "Select a numbered point, box or mask above the layout, then drag to place it. Resize boxes and masks with their handles. Masks scale about their own center and overflow is clipped. Numbers remain fixed. Unlisted positions default to center; coincident points spread left to right. Layout is approximate."

    def apply(self, character_count=2, building_pipe=None, mask_transforms="{}", **values):
        transforms = read_mask_transforms(mask_transforms)
        def settings(i):
            result = {key: values.get(f"character{i}_{key}", getattr(Slot(i), key)) for key in ROLE_FIELDS["position"] if key != "mask_transform"}
            result["mask_transform"] = transforms.get(i, (0., 0., 1.))
            if result["geometry"] not in ("point", "box"):
                raise ValueError(f"Character {i}: choose point or box.")
            return result
        return (apply_role(building_pipe, "position", character_count, settings),)


class RSMultiCharacterMask(BuilderNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "character_id": ("INT", {"default": 1, "min": 1, "max": 10,
                "tooltip": "Match this number to the Character Prompt row."}),
            "enabled": ("BOOLEAN", {"default": True,
                "tooltip": "Off removes this character's mask and restores its point/box settings."}),
            "margin": ("INT", {"default": 24, "min": 0, "max": 128,
                "tooltip": "Expand the white region in source-mask pixels. Leave room for hair, clothes and interaction."}),
            "threshold": ("FLOAT", {"default": .5, "min": 0., "max": 1., "step": .01,
                "tooltip": "Pixels above this value become white. Gray is not a continuous prompt strength."}),
        }, "optional": {"building_pipe": (BUILD_PIPE_TYPE,),
                          "mask": ("MASK", {"tooltip": "One full-canvas mask. White selects this character; black excludes it. Parts moved or enlarged outside the canvas are clipped."}),
                          "offset_x": ("FLOAT", {"default": 0., "min": -1., "max": 1., "step": .01,
                              "tooltip": "Horizontal shift as a fraction of canvas width. Positive moves right; outside is clipped."}),
                          "offset_y": ("FLOAT", {"default": 0., "min": -1., "max": 1., "step": .01,
                              "tooltip": "Vertical shift as a fraction of canvas height. Positive moves down; outside is clipped."}),
                          "scale": ("FLOAT", {"default": 1., "min": .05, "max": 4., "step": .01,
                              "tooltip": "Uniform size ratio about the canvas centre: 0.5 half, 1 original, 2 double. Keeps aspect ratio; outside is clipped."})},
                "hidden": {"unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = (BUILD_PIPE_TYPE, "MASK")
    RETURN_NAMES = ("building_pipe", "region_mask")
    DESCRIPTION = "Use a silhouette or painted MASK for one numbered character. Shift and scale about the canvas centre, then expand the white area; overflow is clipped without wrapping. Overrides its point/box in any builder order. Overlaps share captions; outside uses the common prompt. Guides prompt attention, not exact pose. MOSS native converts masks to enclosing boxes; their shapes are not preserved."

    def apply(self, character_id=1, enabled=True, margin=24, threshold=.5, building_pipe=None, mask=None, unique_id=None,
              offset_x=0., offset_y=0., scale=1.):
        if type(enabled) is not bool:
            raise ValueError("Mask enabled must be true or false.")
        region = prepare_mask(mask, threshold, margin, offset_x, offset_y, scale) if enabled else None
        pipe = update_slot(building_pipe, character_id, region_mask=region, body_parts=(), body_part_strength=0.)
        import torch
        preview = region.tensor()[None] if region is not None else torch.zeros((1, 64, 64))
        images = []
        if region is not None and unique_id is not None:
            import hashlib
            from pathlib import Path
            import folder_paths
            import numpy as np
            from PIL import Image
            filename = hashlib.sha256(f"{region.width}x{region.height}:".encode()+region.packed).hexdigest()+".png"
            directory = Path(folder_paths.get_temp_directory()) / "RS_CharacterMasks"
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / filename
            if not target.exists():
                Image.fromarray((preview[0].numpy()*255).astype(np.uint8)).save(target)
            images.append({"filename": filename, "subfolder": "RS_CharacterMasks", "type": "temp"})
        return {"ui": {"images": images}, "result": (pipe, preview)}


class RSMultiCharacterFinalize:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"building_pipe": (BUILD_PIPE_TYPE,)}}

    RETURN_TYPES = (PIPE_TYPE,)
    RETURN_NAMES = ("character_pipe",)
    FUNCTION = "build"
    CATEGORY = "RS MultiCharacter/Characters"
    DESCRIPTION = "Finish the assembled slots for Sampler/Detailer. Character numbers determine ordering, not node order. Missing prompts are reported here. LoRA and Position are optional; defaults are None and center. Up to 10 character/text regions; quality is not guaranteed as count increases."

    def build(self, building_pipe):
        return (finalize(building_pipe),)
