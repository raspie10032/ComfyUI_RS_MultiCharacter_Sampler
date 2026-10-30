# Experimental Anima 2B 3D pose example

Drag **[anima-native-pose.png](anima-native-pose.png)** onto ComfyUI. This is an actual generated PNG with the complete 14-node / 14-link workflow, native skinned scene and prompt metadata embedded. It is not a screenshot or an image containing only generation settings.

Use an Anima-capable core that includes **ModelPatchLoader / AnimaLLLiteApply**. Select your installed Anima 2B diffusion model, Qwen 0.6B encoder and Qwen Image VAE. Download `anima_3dpose_outline_7000.safetensors` from [toyxyz/Anima_ControlNet-LLLite](https://huggingface.co/toyxyz/Anima_ControlNet-LLLite) into `ComfyUI/models/model_patches` (or an extra model-patch directory), refresh the model list and select it in Load Model Patch. The pose adapter is downloaded separately, not by this node.

The example uses a global `anima/RSCV5_Anima-final42330-comfy.safetensors` style LoRA at 0.9. Choose your own matching LoRA or bypass that loader. Model weights and the style LoRA are not included. No character LoRA or image reference is used. Change the scene through **Open 3D editor** and **Apply to node**; character numbers correspond to Prompt slots.

Two independent paths are connected:

- `building_pipe` → Character Prompt → Finalize → sampler `character_pipe`: numbered silhouettes and character ownership.
- `pose_image` → Apply Anima LLLite → sampler MODEL: learned pose guidance. Mask-only use does not need this adapter.

768×1024, 30 steps, CFG 4.5, Euler ancestral / SGM uniform, pose strength 1 throughout denoising. Keep the sampler/editor aspect ratios equal. This two-person raised-arm example demonstrates integration, not precise hand/contact control. [Setup and limitations](../../docs/pose3d.md) · [Component comparisons](../../docs/pose3d-validation.md).

## Krea2 Turbo and MOSS pose adapters

Drag **[krea2-pose.png](krea2-pose.png)**, **[moss-native-pose.png](moss-native-pose.png)** or **[moss-regional-pose.png](moss-regional-pose.png)** onto ComfyUI. Each PNG contains an actual output, the API prompt and a complete 9-node / 10-link workflow. Select your installed matching diffusion model, text encoder and VAE. A current core with Krea2/MOSS support is required. The tested core was `5cc4b87`.

The 3D node now exposes an additional final `scene_json` output. Connect it to **RS 3D Pose Adapter (Krea2 / MOSS · Experimental)** with the base MODEL and matching VAE. Connect the adapter's MODEL to the standard RS sampler. Keep `building_pipe` connected through Prompt and Finalize for character ownership. Existing 3D outputs keep their slot numbers. Missing adapter weights download on first actual use, with progress and checksum verification.

These examples use two adult women with different hair and clothing, no style/character LoRA and no pose words. The left person raises an arm. Krea2 uses 10 steps / CFG 1 / full pose interval; MOSS uses 50 steps / CFG 4 / pose interval 0–0.5. Both use 768×1024, seed 421030, Euler ancestral and SGM uniform. MOSS native retains learned color/depth pose control while converting numbered character masks to boxes. The regional example retains silhouette routing.

[Setup and limitations](../../docs/pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental) · [Real generation comparison and validation](../../docs/pose3d-krea-moss-validation.md).

For MOSS, start with the native example (`layout_method=moss_native`). New samplers can keep `auto`, which selects native JSON when the MOSS 3D pose adapter is active. Existing explicit choices are preserved.

This recommended path combines native caption/box layout
with trained color/depth pose guidance. The resident follow-up compares adapter
OFF/ON, a seated left person and swapped character captions at the same seed.
See the [four-image comparison](moss-native-audit.jpg) and
[conditions and limitations](../../docs/pose3d-krea-moss-validation.md#moss-native-json-follow-up-on-the-installed-resident).
Native mode converts silhouette masks to boxes; it does not use RS regional
boundary-strength routing. The seated sample follows the pose without creating
a chair, and style-LoRA-related extra-person failures are still unresolved.

## Genshin Impact workflow PNGs

For 1.0.10, use **[Krea 2: Jean and Eula](genshin-krea2-pose.png)** or
**[MOSS native: Jean and Eula](genshin-moss-native-pose.png)**. Save the original
PNG and drop it onto ComfyUI; each embeds the exact tested API prompt, full
9-node / 10-link workflow and 3D scene. These are the raised-arm, first-seed ON
results from the [36-image audit](../../docs/pose3d-genshin-diverse-validation.md).
Select your matching installed models; there is no style/character LoRA.

[한국어 연결·사용 가이드](../../docs/pose3d-krea-moss-guide.ko.md) ·
[English setup](../../docs/pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental).
