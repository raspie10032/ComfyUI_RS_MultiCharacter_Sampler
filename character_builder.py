# SPDX-License-Identifier: GPL-3.0-only
"""Order-independent, immutable editing of numbered character slots."""
from dataclasses import dataclass, replace

from .characters import Character, CharacterPipe, TextRegion, PIPE_TYPE, LORA_MODES, validate_lora_mode

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


@dataclass(frozen=True)
class BuildPipe:
    slots: tuple = ()
    prompt_count: int | None = None
    lora_application_mode: str = "precision"


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


def finalize(pipe):
    if not isinstance(pipe, BuildPipe):
        raise ValueError("Connect a building pipe first. / 조립 파이프를 연결해 주세요. / 組み立てパイプを接続してください。")
    if pipe.prompt_count is None:
        raise ValueError("Connect a Character Prompts node anywhere before Finalize. / 최종 파이프 앞에 캐릭터 프롬프트 노드를 연결해 주세요. / プロンプトノードを接続してください。")
    chars, texts = [], []
    for s in pipe.slots:
        if s.number > pipe.prompt_count or not s.enabled:
            continue
        if s.prompt is None or not s.prompt.strip():
            raise ValueError(f"Character {s.number}: connect a nonempty STRING to the matching Prompt row, or disable that row. / 캐릭터 {s.number}: 프롬프트 노드의 해당 번호에 STRING을 연결하거나 그 행의 사용을 꺼 주세요. / 同じ番号のプロンプトに文字列を接続するか無効にしてください。")
        Character(s.prompt, x=s.x, y=s.y, lora_name=s.lora_name,
                  lora_strength=s.strength_model, lora_clip_strength=s.strength_clip)
        box = slot_box(s)
        if s.kind == "text":
            if s.geometry != "box":
                raise ValueError(f"Character {s.number}: text needs a Position node in box mode. / 글자 영역은 위치 노드를 상자로 설정해 주세요. / 文字領域にはボックス位置が必要です。")
            if s.lora_name != "None":
                raise ValueError(f"Character {s.number}: text regions do not use character LoRAs; choose None. / 글자 영역의 LoRA는 None으로 설정해 주세요. / 文字領域のLoRAはNoneにしてください。")
            texts.append(TextRegion(s.prompt, "", s.x, s.y, box, s.literal_text))
        else:
            chars.append(Character(s.prompt, "", s.x, s.y, box, lora_name=s.lora_name,
                                   lora_strength=s.strength_model, lora_clip_strength=s.strength_clip))
    if not chars and not texts:
        raise ValueError("Enable at least one nonempty prompt. / 최소 한 개의 프롬프트를 켜 주세요. / 少なくとも1つのプロンプトを有効にしてください。")
    return CharacterPipe(tuple(chars), text_regions=tuple(texts), lora_application_mode=pipe.lora_application_mode)


def count_input():
    return ("INT", {"default": 2, "min": 1, "max": 10,
        "tooltip": "Show all slots 1–N together. Prompt count determines the active regions; LoRA/Position counts determine which settings they supply. / 1~N번 설정을 함께 표시합니다. 최종 인원수는 프롬프트 노드 기준입니다."})


ROLE_FIELDS = {
    "prompt": ("prompt", "enabled", "kind", "literal_text"),
    "lora": ("lora_name", "strength_model", "strength_clip"),
    "position": ("geometry", "x", "y", "width", "height"),
}


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
        return {"required": fields, "optional": {"building_pipe": (BUILD_PIPE_TYPE,)}}

    DESCRIPTION = "View all character positions and their layout together. Choose XY or a box per row. Unlisted positions default to center. Coincident points spread left to right by number. Finalize shows the complete line; layout is a guide, not a composition guarantee."

    def apply(self, character_count=2, building_pipe=None, **values):
        def settings(i):
            result = {key: values.get(f"character{i}_{key}", getattr(Slot(i), key)) for key in ROLE_FIELDS["position"]}
            if result["geometry"] not in ("point", "box"):
                raise ValueError(f"Character {i}: choose point or box.")
            return result
        return (apply_role(building_pipe, "position", character_count, settings),)


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
