# Experimental Anima 2B 3D pose example

Drag **[anima-native-pose.png](anima-native-pose.png)** onto ComfyUI. This is an actual generated PNG with the complete 14-node / 14-link workflow, native skinned scene and prompt metadata embedded. It is not a screenshot or an image containing only generation settings.

Use an Anima-capable core that includes **ModelPatchLoader / AnimaLLLiteApply**. Select your installed Anima 2B diffusion model, Qwen 0.6B encoder and Qwen Image VAE. Download `anima_3dpose_outline_7000.safetensors` from [toyxyz/Anima_ControlNet-LLLite](https://huggingface.co/toyxyz/Anima_ControlNet-LLLite) into `ComfyUI/models/model_patches` (or an extra model-patch directory), refresh the model list and select it in Load Model Patch. The pose adapter is downloaded separately, not by this node.

The example uses a global `anima/RSCV5_Anima-final42330-comfy.safetensors` style LoRA at 0.9. Choose your own matching LoRA or bypass that loader. Model weights and the style LoRA are not included. No character LoRA or image reference is used. Change the scene through **Open 3D editor** and **Apply to node**; character numbers correspond to Prompt slots.

Two independent paths are connected:

- `building_pipe` → Character Prompt → Finalize → sampler `character_pipe`: numbered silhouettes and character ownership.
- `pose_image` → Apply Anima LLLite → sampler MODEL: learned pose guidance. Mask-only use does not need this adapter.

768×1024, 30 steps, CFG 4.5, Euler ancestral / SGM uniform, pose strength 1 throughout denoising. Keep the sampler/editor aspect ratios equal. This two-person raised-arm example demonstrates integration, not precise hand/contact control. [Setup and limitations](../../docs/pose3d.md) · [Component comparisons](../../docs/pose3d-validation.md).
