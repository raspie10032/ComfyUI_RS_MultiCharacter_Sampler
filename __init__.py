# SPDX-License-Identifier: GPL-3.0-only
from .characters import RSMultiCharacterPrompts
from .character_builder import (RSMultiCharacterPrompt, RSMultiCharacterLoRA,
                                RSMultiCharacterPosition, RSMultiCharacterFinalize)
from .nodes import RSMultiCharacterSampler, RSMultiCharacterLoadImage
from .detailer import RSMultiCharacterDetailer
from .detector_bundle import RSMultiCharacterDetectionLoader
from .wd_tagger import RSMultiCharacterTaggerLoader

NODE_CLASS_MAPPINGS = {
    "RSMultiCharacterPrompt": RSMultiCharacterPrompt,
    "RSMultiCharacterLoRA": RSMultiCharacterLoRA,
    "RSMultiCharacterPosition": RSMultiCharacterPosition,
    "RSMultiCharacterFinalize": RSMultiCharacterFinalize,
    "RSMultiCharacterPrompts": RSMultiCharacterPrompts,
    "RSMultiCharacterSampler": RSMultiCharacterSampler,
    "RSMultiCharacterLoadImage": RSMultiCharacterLoadImage,
    "RSMultiCharacterDetailer": RSMultiCharacterDetailer,
    "RSMultiCharacterDetectionLoader": RSMultiCharacterDetectionLoader,
    "RSMultiCharacterTaggerLoader": RSMultiCharacterTaggerLoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "RSMultiCharacterPrompt": "RS Character Prompt",
    "RSMultiCharacterLoRA": "RS Character LoRA",
    "RSMultiCharacterPosition": "RS Character Position",
    "RSMultiCharacterFinalize": "RS Finalize Character Pipe",
    "RSMultiCharacterPrompts": "RS MultiCharacter Prompts",
    "RSMultiCharacterSampler": "RS MultiCharacter Sampler (Giyeok Fix)",
    "RSMultiCharacterLoadImage": "RS MultiCharacter Load Image",
    "RSMultiCharacterDetailer": "RS MultiCharacter Detailer",
    "RSMultiCharacterDetectionLoader": "RS Detection Combine Loader",
    "RSMultiCharacterTaggerLoader": "RS Character Tagger Loader",
}
WEB_DIRECTORY = "./web"
__version__ = "0.2.1"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
