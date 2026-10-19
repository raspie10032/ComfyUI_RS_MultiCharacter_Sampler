# MOSS JSON + regional attention experiment (2026-10-20)

Experimental branch: `codex/moss-hybrid-layout`, based on `3a4433f`.
The installed release remains 0.2.3.

## Implementation

The new experimental `layout_method=moss_hybrid` encodes the exact same native
layout JSON as `moss_native` for common positive conditioning. It also encodes
the original character/text captions separately and installs the existing MOSS
joint attention routing. Every region needs an explicit box. Other model
families reject both MOSS JSON modes. NovelAI weight syntax and per-character
CLIP LoRAs retain the existing native JSON restrictions. This experiment used
only one global model LoRA, not character LoRAs.

`moss_native` still skips regional routing. `regional` still encodes the plain
common prompt and installs routing. Audit output records the mode, JSON when
used, and whether routing was installed. The mode survives generated-image
metadata and `use_image_settings` replay.

Official schema: https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md#layout-prompts-experimental

## Actual GPU experiment

- MOSS Image SFT BF16, Qwen3.5 9B INT8 text encoder, Flux2 VAE.
- `moss/akhaliq_4step_v2_7258a71.safetensors`, global strength 1.0.
- 1024x768, Euler/simple, 4 steps, CFG 1.0.
- Nahida left, Sigewinne right, chiffon dresses, flower garden, bottom title
  `Arcalive\nAI ART Channel`. Two character boxes plus a text box.
- Three fixed seeds: `145451379171813`, `145451379171814`, `145451379171815`.
- Three modes per seed, nine images. The API graphs differ only in mode and
  measurement label within a seed. Native JSON strings match between native
  and hybrid cases. No image postprocessing was applied to the original PNGs.
- Four real model evaluations per image, with 168 cross/self attention calls
  each in regional and hybrid cases, and zero in native-only cases. The model
  audit records 168 patched weight keys from the acceleration LoRA.
- The common JSON encoding was 517 tokens versus 105/111 character tokens and
  28 text-region tokens in the first seed's hybrid evaluation.

Mean noise-removal time over the three seeds: native **2.321 s**, regional
**2.854 s**, hybrid **3.005 s**. These are synchronized sampling timings only;
they exclude encoder/model setup, VAE decoding, file writes and HTTP overhead.
The runs were sequential and include warmup effects, not a general benchmark.

## Observations and limits

Both characters remained distinguishable in all nine matched outputs. Native
JSON gave the clearest standalone bottom title and garden in this small set.
Regional-only kept the garden but integrated the title into the illustration,
with varying size/contrast. Hybrid repeatedly lost the garden and title
contrast. **This experiment does not demonstrate a hybrid quality improvement.**

Three additional first-seed hybrid cases tested boundary 0 alone, initial
character gain 1.0 alone, and a combined gentle case (common prior 1.0, no
additional common boost, gain 1.0, boundary 0). Background and text improved
partly in the combined case but remained faded. The combined case changes
multiple factors and cannot isolate a cause.

The routing changes how native JSON tokens interact with images and how text
attention mass is allocated. Native layout semantics may be disturbed by that
change and by separate repeated captions. This is a hypothesis, not an
established mechanism. An exact token-span-aware JSON implementation, other
step counts, non-distilled MOSS, conflicting layouts, more characters and
per-character LoRAs have not been tested here.

## Validation and local evidence

The real tiny CPU MOSS integration verifies all three paths, actual sampler
execution, restored model options and exact hybrid latent replay from saved
settings. Synthetic text embeddings and a synthetic VAE in that test do not
prove image quality. The GPU artifacts provide the image-quality evidence.

Local experiment root:
`/var/home/raspie/Documents/Codex/RS_MC_moss_hybrid_20261020/`.
It contains `REPORT.md`, `index.html`, `base.api.json`, a resumable
`run_comparison.py`, measurement helper nodes and `validation/` receipts,
histories, timing/attention audits and original PNGs. The API graphs reference
local model filenames and temporary audit nodes and are not ordinary UI
workflow JSON files. Original PNGs preserve generation metadata, not workflows.
