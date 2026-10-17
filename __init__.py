# SPDX-License-Identifier: GPL-3.0-only
from .characters import RSMultiCharacterPrompts
from .nodes import RSMultiCharacterSampler, RSMultiCharacterLoadImage
from .detailer import RSMultiCharacterDetailer
from .detector_bundle import RSMultiCharacterDetectionLoader
from .wd_tagger import RSMultiCharacterTaggerLoader

NODE_CLASS_MAPPINGS = {
    "RSMultiCharacterPrompts": RSMultiCharacterPrompts,
    "RSMultiCharacterSampler": RSMultiCharacterSampler,
    "RSMultiCharacterLoadImage": RSMultiCharacterLoadImage,
    "RSMultiCharacterDetailer": RSMultiCharacterDetailer,
    "RSMultiCharacterDetectionLoader": RSMultiCharacterDetectionLoader,
    "RSMultiCharacterTaggerLoader": RSMultiCharacterTaggerLoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "RSMultiCharacterPrompts": "RS MultiCharacter Prompts",
    "RSMultiCharacterSampler": "RS MultiCharacter Sampler (Beta)",
    "RSMultiCharacterLoadImage": "RS MultiCharacter Load Image",
    "RSMultiCharacterDetailer": "RS MultiCharacter Detailer",
    "RSMultiCharacterDetectionLoader": "RS Detection Combine Loader",
    "RSMultiCharacterTaggerLoader": "RS Character Tagger Loader",
}
WEB_DIRECTORY = "./web"
__version__ = "0.1.2"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
