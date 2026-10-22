# SPDX-License-Identifier: GPL-3.0-only
from .characters import RSMultiCharacterPrompts
from .pose_nodes import RSMultiCharacterPoseMasks
from .interaction import RSMultiCharacterInteraction
from .character_builder import (RSMultiCharacterPrompt, RSMultiCharacterLoRA,
                                RSMultiCharacterPosition, RSMultiCharacterFinalize, RSMultiCharacterMask)
from .nodes import RSMultiCharacterSampler, RSMultiCharacterLoadImage
from .detailer import RSMultiCharacterDetailer
from .detector_bundle import RSMultiCharacterDetectionLoader
from .wd_tagger import RSMultiCharacterTaggerLoader
from .mask_drawing import RSMultiCharacterMaskDraw
from .image_reference import RSMultiCharacterReference

NODE_CLASS_MAPPINGS = {
    "RSMultiCharacterPoseMasks": RSMultiCharacterPoseMasks,
    "RSMultiCharacterInteraction": RSMultiCharacterInteraction,
    "RSMultiCharacterReference": RSMultiCharacterReference,
    "RSMultiCharacterPrompt": RSMultiCharacterPrompt,
    "RSMultiCharacterLoRA": RSMultiCharacterLoRA,
    "RSMultiCharacterPosition": RSMultiCharacterPosition,
    "RSMultiCharacterMask": RSMultiCharacterMask,
    "RSMultiCharacterMaskDraw": RSMultiCharacterMaskDraw,
    "RSMultiCharacterFinalize": RSMultiCharacterFinalize,
    "RSMultiCharacterPrompts": RSMultiCharacterPrompts,
    "RSMultiCharacterSampler": RSMultiCharacterSampler,
    "RSMultiCharacterLoadImage": RSMultiCharacterLoadImage,
    "RSMultiCharacterDetailer": RSMultiCharacterDetailer,
    "RSMultiCharacterDetectionLoader": RSMultiCharacterDetectionLoader,
    "RSMultiCharacterTaggerLoader": RSMultiCharacterTaggerLoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "RSMultiCharacterPoseMasks": "RS OpenPose Masks (Experimental)",
    "RSMultiCharacterInteraction": "RS Character Interaction",
    "RSMultiCharacterReference": "RS Image Reference (Experimental · Not Recommended)",
    "RSMultiCharacterPrompt": "RS Character Prompt",
    "RSMultiCharacterLoRA": "RS Character LoRA",
    "RSMultiCharacterPosition": "RS Character Position",
    "RSMultiCharacterMask": "RS Character Mask",
    "RSMultiCharacterMaskDraw": "RS Character Mask Drawing",
    "RSMultiCharacterFinalize": "RS Finalize Character Pipe",
    "RSMultiCharacterPrompts": "RS MultiCharacter Prompts",
    "RSMultiCharacterSampler": "RS MultiCharacter Sampler (Hangeul)",
    "RSMultiCharacterLoadImage": "RS MultiCharacter Load Image",
    "RSMultiCharacterDetailer": "RS MultiCharacter Detailer",
    "RSMultiCharacterDetectionLoader": "RS Detection Combine Loader",
    "RSMultiCharacterTaggerLoader": "RS Character Tagger Loader",
}
WEB_DIRECTORY = "./web"
__version__ = "1.0.0"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
