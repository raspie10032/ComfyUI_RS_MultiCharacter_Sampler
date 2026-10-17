# SPDX-License-Identifier: GPL-3.0-only
"""Original prompt text travels in one dedicated, immutable pipe."""
from dataclasses import dataclass
import math

PIPE_TYPE = "RS_MC_CHARACTER_PIPE"


@dataclass(frozen=True)
class Character:
    prompt: str
    uc: str = ""
    x: float = .5
    y: float = .5

    def __post_init__(self):
        if not isinstance(self.prompt, str) or not isinstance(self.uc, str):
            raise ValueError("Character prompts must be text.")
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or
               not math.isfinite(v) or not 0 <= v <= 1 for v in (self.x, self.y)):
            raise ValueError("Character X/Y must be finite numbers from 0 to 1.")

    @property
    def center(self):
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class CharacterPipe:
    characters: tuple
    prompt: str | None = None
    negative_prompt: str | None = None
    syntax: str = "ComfyUI"
    # Serialized snapshot avoids shared mutable state between consumers.
    generation_json: str | None = None

    def __post_init__(self):
        if not isinstance(self.characters, tuple) or not 1 <= len(self.characters) <= 10:
            raise ValueError("Use 1–10 nonempty active character slots. / 활성 캐릭터를 1~10명 입력해 주세요.")
        if any(not isinstance(c, Character) or not c.prompt.strip() for c in self.characters):
            raise ValueError("Every active character needs a nonempty prompt.")
        if self.syntax not in ("ComfyUI", "NovelAI"):
            raise ValueError("Unsupported prompt syntax.")
        if any(v is not None and not isinstance(v, str) for v in (self.prompt, self.negative_prompt, self.generation_json)):
            raise ValueError("Invalid character pipe text.")


class RSMultiCharacterPrompts:
    @classmethod
    def INPUT_TYPES(cls):
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
        return {"required": fields}

    RETURN_TYPES = (PIPE_TYPE,)
    RETURN_NAMES = ("character_pipe",)
    FUNCTION = "build"
    CATEGORY = "RS MultiCharacter"
    DESCRIPTION = "1–10 character prompts with X/Y positions. Coincident positions spread left to right in slot order. More characters do not guarantee quality. / 처리수가 많을수록 품질을 보장하지 못합니다."

    def build(self, character_count=5, **values):
        if type(character_count) is not int or not 1 <= character_count <= 10:
            raise ValueError("Choose 1–10 character slots.")
        chars = []
        for i in range(1, character_count + 1):
            if not values.get(f"character{i}_enable", True):
                continue
            text = values.get(f"character{i}", "")
            if not isinstance(text, str):
                raise ValueError(f"Character {i} prompt must be text.")
            if text.strip():
                chars.append(Character(text, values.get(f"character{i}_uc", ""),
                    values.get(f"character{i}_x", .5), values.get(f"character{i}_y", .5)))
        return (CharacterPipe(tuple(chars)),)
