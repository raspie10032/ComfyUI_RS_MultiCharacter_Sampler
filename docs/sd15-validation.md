# SD1.5 regional generation experiment

**Experimental support; unstable character counts and attribute separation.**
The real checkpoint trial stopped after the four images below at the user's
request. No additional quality tuning or SD1.5 detailer run was performed.

The ordinary SD1.5 checkpoint path uses the existing U-Net attention routing
with separate CLIP-L sequences. Unlike SDXL, SD1.5 has no pooled ADM vector.
Use one `CheckpointLoaderSimple` for MODEL, CLIP and VAE, followed by the
existing character pipe and sampler; no extra node is needed.

This experiment uses `v1-5-pruned-emaonly.safetensors` from the
[SD1.5 checkpoint mirror](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5),
revision `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`.
Expected file size: 4,265,146,304 bytes. Expected SHA-256:
`6ce0161689b3853acaa03779ec93eafe75a02f4ced659bee03f50797806fa2fa`.
This is the original general-purpose checkpoint, not an anime fine-tune.

The initial two-character settings are 768x512, 30 steps, CFG 7,
Euler ancestral / normal, common prior 0.3, character gain 1.3,
spatial separation 0.5, boundary hold 3 and decrement 0.2.
The two prompts request short black hair / red jacket and long blonde hair /
white blouse. Swapping only these prompts at a fixed seed checks whether
appearance follows the requested regions.

## Scope

The regional sampler accepts ordinary 4-channel SD1.5 checkpoints identified
by native ComfyUI `SD15` configuration. This is not support for SD2,
inpainting, instruct-pix2pix, ControlNet or other attention patches.
The UI's existing 10 input slots are unchanged; a two-person experiment does
not establish quality or exact counts at larger character counts. LoRA and
fine-tune quality must be checked separately.

PNG and WebP metadata identify `sd1.5-spatial-alpha-1` and retain the original
character captions and local settings. The Load Image node restores the pipe;
model selection remains explicit.

## Observed results

All four public-node requests completed on native ComfyUI `15eb748` using an
RTX 4070 Ti SUPER. Only character text was swapped within each seed pair; XY,
common text and sampling parameters were retained. Visual inspection found:

| Seed | Text order | Visible people | Observation |
| --- | --- | --- | --- |
| 617201 | Black/red, blonde/white | 3 | Extra blonde figure; red/black garment attributes reversed on the left |
| 617201 | Blonde/white, black/red | 2 | Left/right appearance changes with text; blue/white garments reversed, right figure cropped |
| 230415 | Black/red, blonde/white | 2 | Both figures have black hair; requested blonde hair is missing |
| 230415 | Blonde/white, black/red | 3 | Blonde on the left and red jacket on the right, with an extra middle figure |

This is evidence of execution and prompt influence, **not stable two-character
generation**. Four images do not establish a general success rate. There is no
claim that the same quality limits apply to every SD1.5 fine-tune. No LoRA,
anime fine-tune, higher character count or SD1.5 detailer was tested.

Native CPU integrations also passed on ComfyUI `v0.3.76`, `15eb748` and
`5cc4b87`. These use a small random U-Net and synthetic text/VAE to check native
sampling, routing restoration, metadata and wrong-model/encoder rejection;
they do not test image quality. The corresponding suites ran 72 tests:
69 passed / 3 skipped, 71 passed / 1 skipped, and 72 passed respectively.
The skipped cases are architectures absent from the host snapshot.

Local requests, ComfyUI histories, original PNGs, download hash, environment
and CPU logs are retained in `RS_MC_sd15/validation` beside this checkout.
The downloaded checkpoint is SHA-256 verified against the pinned upstream
file. The experiment extends compatibility commit `b287ca2` in the separate
`codex/sd15-validation` branch; this report is not evidence of a public release
or an update to the everyday installation.

## Reproduce

Place the checkpoint in `ComfyUI/models/checkpoints` and load
[`two-characters-sd15.json`](../examples/two-characters-sd15.json).
For API use, [`two-characters-sd15-api.json`](../examples/two-characters-sd15-api.json)
contains the same settings with seed 617201. Keep that seed fixed and swap
only the character text fields for the paired comparison.
