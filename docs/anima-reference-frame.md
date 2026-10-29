# Anima reference frame adapter (experimental)

This is the Anima-only reference-frame backend used by the numbered Image Reference input; advanced adapter nodes expose additional controls. Adapted from [ElectronGirl/ComfyUI-Anima-Ref-Adapter](https://github.com/ElectronGirl/ComfyUI-Anima-Ref-Adapter) at `af9a438d` under Apache-2.0. See `ANIMA-REF-ADAPTER-LICENSE` for the preserved license.

## Connect

With the ordinary Image Reference node, keep `anima_method=reference_frame`. Select either an Anima **2B (28 blocks)** or **2.9B (40 blocks)** checkpoint in the model loader. The sampler detects its architecture and automatically prepares the matching pinned adapter (about 88 MiB). Model choice is yours; quality and generation cost can differ. No separate model adapter node is required. OFF/strength 0 prepares no adapter.

The expanded 2.9B checkpoint itself must be downloaded separately. It requires a ComfyUI core that recognizes 40-block Anima; update ComfyUI if the model cannot load. The converted adapter maps the original 28 trained blocks around 12 inserted blocks. All 40 model blocks still run; the 12 inserted blocks have no reference-adapter LoRA hooks. This conversion is not a newly trained 2.9B reference model.

For advanced controls, download the appropriate weights into `ComfyUI/models/loras` and select them explicitly in the adapter node below. Use `anima_ref_adapter_pilot_r32.safetensors` for 2B and `anima_ref_adapter_pilot_r32_29B.safetensors` for 2.9B. Wrong variants and incomplete module coverage produce an error. Follow the upstream weight license; ordinary style/character LoRAs are not reference adapters.

`Load Diffusion Model → RS Anima Reference Adapter (Experimental) → RS MultiCharacter Sampler`

For a **global reference**, connect `Load Image` to the adapter's optional IMAGE. For **numbered character references**, leave that IMAGE disconnected, then connect each image to `RS Anima Character Reference` and match its number to Prompt/Position, as with per-character LoRAs. Connect their BUILDING_PIPE through Finalize to the sampler. Building-node order does not matter; the last enabled value for a repeated number wins. Do not combine the global image with numbered references.

The sampler fits references inside a reference canvas and VAE-encodes each distinct source/grid once per generation. Default reference scale 1 uses the target size. Scale 0.8 uses 80% of each side, rounded to 16 pixels, without changing target resolution. It packs the smaller reference token grid with the target, rather than resizing it back up. Reference rotary coordinates preserve the target spatial extent. This experimental change can affect identity, fine details and composition. The model must be Anima. Native KSampler and the detailer are deliberately rejected by this experiment, instead of silently ignoring the reference. The RS progressive sampler uses the same reference guider through its stage integrator. Character masks/prompts still control target regions. A global reference affects the **whole image**, including other characters.

Numbered references use separate source-conditioned predictions and blend their results in the matching point/box/mask regions, like precision LoRA application. A source branch cannot read the other reference image. Uncovered pixels use the ordinary prediction; overlapping regions blend their active references with normalized weights. This prevents shared reference hidden states but does **not** guarantee perfect final-image identity isolation: image denoising still couples adjacent regions. Keep one character per reference image. OFF/strength 0 removes only that numbered reference; mask and prompt remain. More references require more predictions, so this can be significantly slower. Fidelity and style preservation remain experimental.

- **strength**: adapter multiplier, default 1. Set 0 to bypass all reference processing.
- **reference_guidance**: reference influence in the author's guidance formula, default 4.5. With one global image, 1 omits the extra unreferenced prediction; this saves compute **and changes the image**. Numbered references retain the ordinary background prediction. Zero bypasses reference processing.
- **correction**: APG (default), rescale or none, following the upstream guidance math.
- **reference_scale** (default 1): reference side-length multiplier, 0.5–1.0. For example, target 1024×768 with scale 0.8 uses an 816×608 reference canvas: 1,938 reference tokens versus 3,072 at full size. This reduces reference tokens by 36.9%, not the whole generation cost. Global and independent numbered references support it.
- **cache_text_kv** (default OFF): reuse identical text projections inside one generation, up to 256 MiB. Retain a bounded subset instead of cycling through evictions. Automatically disabled with per-character LoRAs. It cannot cache the changing reference-image self-attention features. Initial measurements found negligible speed improvement for up to 256 MiB extra memory, so this optional cache defaults OFF.

Adapters, temporary hooks and GPU caches are scoped to a generation and released even after cancellation/error. Per-character LoRA overrides are suspended during the unreferenced guidance prediction and restored afterwards. Unsupported combinations with the older per-character image-reference method are rejected.

## Optimization experiment

The benchmark sets the following internal `model_options`; they are not additional user-interface controls yet:

- `rs_reference_follow_resolution=True`: fit and encode the reference for each progressive target grid. All required VAE encodes run before sampling so VAE/model residency does not alternate between stages.
- `rs_reference_end_step=N`: include references through step N, then use the ordinary positive/negative prediction. Numbered character prompts and regional attention continue after reference removal. Only grids used before this cutoff are encoded. This saves work but can change identity and small details; it is a quality/speed choice.
- `rs_reference_compact_spatial=True`: use one spatial logit-bias row per ownership cell, with unrestricted reference-query rows, instead of a padded square table. Global and independent numbered predictions use it; shared-reference routing keeps its existing implementation. The mathematical priors and connectivity match the dense path, but different GPU attention shapes can change rounding and final pixels. Keep the dense path for paired comparisons.

No reference hidden states or changing image self-attention K/V are reused across denoising steps. The optional text K/V cache remains OFF by default. Benchmarks must report reference schedule, cache setting and reference scale as well as final image size.

An experimental RTX 4070 Ti SUPER comparison at 1728×1152, 30 Euler ancestral/SGM uniform steps, progressive 1152×768 → 1440×960 → 1728×1152, and two independently applied references produced:

| Reference schedule | Earlier experimental implementation | Compact spatial implementation | Peak allocated reduction |
|---|---:|---:|---:|
| Steps 1–16, text cache OFF | 95.38 s | 87.42 s | 314 MiB |
| Steps 1–30 | 219.96 s, cache OFF | 192.96 s, cache ON | 209 MiB |
| Steps 1–16, second seed with overlap, cache OFF | 95.84 s | 88.70 s | 317 MiB |

These are single warm-model measurements including conditioning, sampling and VAE decode, excluding model loading and saving. The second row deliberately states the different cache setting; full-schedule compact/cache-OFF was not measured. The first row preserved broad character features but changed fine facial details. Both overlap results failed to preserve the two reference identities, so the last row is a speed result, not a successful fidelity result. GPU numerical checks matched explicit dense bias rows exactly; BF16 attention outputs differed by at most 0.00390625 in 16 small CUDA cases. Repeated timing and new reference pairs are still required before treating this as a general speed or quality guarantee.

Generation metadata records adapter settings and numbered reference fingerprints for inspection. It does not embed reference pixels or automatically rebuild the reference connection. Keep the original images and save a workflow with the normal ComfyUI image save node if you need that connection. Metadata-only reload requires reconnecting these source images.

## Model and weight sources

- [Anima 2.9B model](https://huggingface.co/Gazingstars123/Anima-2.9B) and its `expand_manifest.json`.
- [Converted 2.9B reference adapter](https://huggingface.co/pamparamm/anima-ref-adapter-2.9B-converted).
- `reference_assets.json` pins adapter revisions and SHA256; downloads and reused files are checked.
- `role_kv` remains a separate **2B-only** adapter. Choose `reference_frame` for 2.9B.

## Validation limits

The initial native CPU tests cover RoPE offsets, cached/uncached equality, target/reference token routing, restoration and bounded cache. GPU results, timings and limitations are recorded in the external experiment directory. Test success does not establish reference fidelity across arbitrary images, quantized checkpoints or LoRAs.

The expanded model mapping and public-node GPU regression results are documented in [Anima 2.9B reference validation](anima29-reference-validation.md).

## Asymmetric v2 development experiment

The advanced adapter node also offers an explicit `Auto: Anima v2 (2B)` choice.
This prepares different weights and a generation-local image K/V backend.
See [scope, limitations and regional routing](anima-reference-v2.md).
The ordinary reference-frame choice and 2.9B conversion are unchanged.
