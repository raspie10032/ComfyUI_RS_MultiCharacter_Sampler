# SPDX-License-Identifier: GPL-3.0-only
from .characters import RSMultiCharacterPrompts
from .pose_nodes import RSMultiCharacterPoseMasks
from .pose3d_node import RSMultiCharacterPose3D
from .pose_estimator import RSImageToPose3D
from .pose_adapter import RS3DPoseAdapter
from .interaction import RSMultiCharacterInteraction
from .character_builder import (RSMultiCharacterPrompt, RSMultiCharacterLoRA,
                                RSMultiCharacterPosition, RSMultiCharacterFinalize, RSMultiCharacterMask)
from .nodes import RSMultiCharacterSampler, RSMultiCharacterLoadImage
from .detailer import RSMultiCharacterDetailer
from .detector_bundle import RSMultiCharacterDetectionLoader
from .wd_tagger import RSMultiCharacterTaggerLoader
from .mask_drawing import RSMultiCharacterMaskDraw
from .image_reference import RSMultiCharacterReference
from .camera_control import RSCameraControl
from .progressive import RSMultiCharacterProgressiveSampler
from .anima_ref_frame import RSAnimaReferenceAdapter, RSAnimaCharacterReference

NODE_CLASS_MAPPINGS = {
    "RSImageToPose3D": RSImageToPose3D,
    "RS3DPoseAdapter": RS3DPoseAdapter,
    "RSMultiCharacterPose3D": RSMultiCharacterPose3D,
    "RSAnimaCharacterReference": RSAnimaCharacterReference,
    "RSAnimaReferenceAdapter": RSAnimaReferenceAdapter,
    "RSMultiCharacterProgressiveSampler": RSMultiCharacterProgressiveSampler,
    "RSCameraControl": RSCameraControl,
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
    "RSImageToPose3D": "RS Image to 3D Pose (Experimental)",
    "RS3DPoseAdapter": "RS 3D Pose Adapter (Krea2 / MOSS · Experimental)",
    "RSMultiCharacterPose3D": "RS 3D Pose Masks (Experimental)",
    "RSAnimaCharacterReference": "RS Anima Character Reference (Experimental)",
    "RSAnimaReferenceAdapter": "RS Anima Reference Frame (Experimental)",
    "RSMultiCharacterProgressiveSampler": "RS Progressive Resolution Sampler",
    "RSCameraControl": "RS Camera Control",
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
from .pipe_compat import shared_pipe_inputs
from . import metadata_notice
from . import app_catalog
from . import app_wildcards

for node_class in NODE_CLASS_MAPPINGS.values():
    shared_pipe_inputs(node_class)

WEB_DIRECTORY = "./web"
__version__ = "1.1.1"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
