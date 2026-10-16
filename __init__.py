# SPDX-License-Identifier: GPL-3.0-only
from .characters import RSMultiCharacterPrompts
from .nodes import RSMultiCharacterSampler, RSMultiCharacterLoadImage

NODE_CLASS_MAPPINGS = {
    "RSMultiCharacterPrompts": RSMultiCharacterPrompts,
    "RSMultiCharacterSampler": RSMultiCharacterSampler,
    "RSMultiCharacterLoadImage": RSMultiCharacterLoadImage,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "RSMultiCharacterPrompts": "RS MultiCharacter Prompts",
    "RSMultiCharacterSampler": "RS MultiCharacter Sampler (Anima Alpha)",
    "RSMultiCharacterLoadImage": "RS MultiCharacter Load Image",
}
WEB_DIRECTORY = "./web"
__version__ = "0.1.0-alpha1"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
