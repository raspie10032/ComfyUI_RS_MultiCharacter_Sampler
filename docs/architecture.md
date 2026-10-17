# Architecture and metadata

## Runtime

`RSMultiCharacterPrompts` validates up to 10 active character texts and XY centers and outputs an immutable `RS_MC_CHARACTER_PIPE`. Hidden, disabled and blank slots are excluded. Empty input is an error. Duplicate centers receive deterministic horizontal offsets; original and effective coordinates are recorded separately.

The sampler independently encodes the common prompt, common negative and each character. Anima's text adapter processes each character separately. Normalized XY centers determine nearest-center regions, then image tokens receive a region owner. This ownership stays active throughout sampling.

For positive cross-attention each image token reads the common text and its own character text. Other characters' text is excluded. A common-text prior biases the shared softmax, while a separate character gain scales the character value vectors. These are different operations; neither is the global CFG value. Negative conditioning uses the common negative only.

Self-attention adds `log(1 - separation)` to foreign-region keys on both CFG branches. At separation zero this extra bias is absent; cross-attention ownership still remains. This is not a trained ControlNet and does not enforce an exact subject count.

At the tested 30-step defaults:

| Sampler step | Common prior | Self-attention separation |
| --- | --- | --- |
| 1–3 | 0.05 | 0.9 |
| 4–6 | 0.35 | 0.7, 0.5, 0.3 |
| 7–9 | 0.55 | 0.1, 0, 0 |
| 10–12 | 0.75 | 0 |
| 13–15 | 0.95 | 0 |
| 16–30 | 1.0 | 0 |

Character value gain starts at 1.7, holds through the early 40%, smoothly returns to 1.0 by 75%, then stays at 1.0. Timing is computed from the actual sigma schedule, not a mutable forward-call counter. The model patcher is cloned; temporary attention forwards are restored in `finally` blocks, including interruptions/errors.

## Experimental SDXL path

SDXL base-family U-Nets use ComfyUI's clone-local `attn1` / `attn2` replacement callbacks, not Anima's adapter. Each character is encoded independently with the checkpoint's dual CLIP. Character token sequences are concatenated only for the native attention K/V projection. Positive queries then read common tokens plus their own region's character tokens; the negative branch reads only native negative tokens. Unequal text lengths are supported. Resolution-aware ownership is recalculated for each U-Net token grid, including odd downsampled sizes.

The common prompt's pooled CLIP-G embedding remains the native global ADM input, with requested size/crop information. Character pooled embeddings are not averaged into this vector because it has no spatial axis. Consequently, a zero common attention prior does not disable all common-prompt influence on SDXL. This design preserves native SDXL conditioning, but does not enforce exact counts or eliminate panel artifacts. The SDXL example uses milder initial strengths than Anima; see [live validation](sdxl-validation.md).

Callbacks are installed only on a cloned ModelPatcher; sampling/forward state and per-forward bias caches are cleared even after errors. Input model attention patches are rejected before installation. Only four-channel SDXL base-family U-Nets are accepted; Refiner and inpainting variants are excluded. No ControlNet or per-character negative routing is added.

## Experimental Krea 2 / MOSS joint-attention paths

These models combine image and text tokens in each transformer block. Common and character text are encoded independently and stay isolated in their native text refiners. On the positive branch, image queries read the common caption, their assigned character caption, and image keys. Character-text queries read their own caption and their image region; common-text queries read common text and all image keys. Cross-region image interaction follows the same boundary schedule. Text priors are normalized by caption length and character gain scales its value vectors.

Krea 2 orders text before image tokens; MOSS orders image tokens before text. MOSS also positions the image after the text on its rotary `f` axis: each separate caption is translated to end at the native text/image boundary, preserving its original distance to the image. Tests compare this rotation with native single-caption Q/K positions. Krea's encoder-layer attention remains native because it mixes tapped layers within each token, not separate captions.

The native ComfyUI optimized-attention override and model wrappers are installed on a cloned patcher. The negative branch uses native text, rotary positions and attention. Branch state is restored after each forward and cleared after sampling, including failures. Unsupported masks/references and existing attention overrides are rejected explicitly. Common weight and boundary release follow actual sampling steps; character gain follows sampling progress. Two to 100 steps are accepted, with existing 30-step defaults unchanged.

Model files, examples and exact live-validation coverage are in [Krea 2 / MOSS validation](krea-moss-validation.md). This is T2I support, not reference-image editing or a guarantee of exact counts or identity.

## Image metadata version 1

PNG stores `Title`, `Description`, `Software`, `Source` and JSON `Comment` text chunks. WebP stores title, description, software and the same ASCII-escaped JSON in EXIF `ExifIFD.UserComment` (tag 37510). No ComfyUI `prompt` graph or `workflow` chunk is embedded by autosave. The Comment's `prompt` member is plain common text.

The NAI-shaped part is:

```json
{
  "prompt": "common positive",
  "uc": "common negative",
  "seed": 123,
  "width": 1536,
  "height": 768,
  "steps": 30,
  "scale": 4.0,
  "sampler": "euler_ancestral",
  "noise_schedule": "sgm_uniform",
  "v4_prompt": {
    "caption": {
      "base_caption": "common positive",
      "char_captions": [
        {"char_caption": "1girl, blonde hair", "centers": [{"x": 0.25, "y": 0.5}]}
      ]
    },
    "use_coords": true,
    "use_order": true,
    "legacy_uc": false
  },
  "v4_negative_prompt": {
    "caption": {
      "base_caption": "common negative",
      "char_captions": [
        {"char_caption": "", "centers": [{"x": 0.25, "y": 0.5}]}
      ]
    },
    "use_coords": false,
    "use_order": false,
    "legacy_uc": false
  }
}
```

The additional `rs_multicharacter` object stores schema `version: 1`, engine `anima-spatial-alpha-1`, `sdxl-spatial-alpha-1`, `krea2-spatial-alpha-1` or `moss-spatial-alpha-1`, prompt syntax, sampler/routing settings, effective centers, slot count and connected loader descriptions. Known standard model, text encoder, VAE and LoRA loaders are recorded by filename and settings. Unrecognized loader chains are explicitly marked unresolved. No credentials, arbitrary graph nodes, absolute model directories or weight files are serialized.

The extension identifies output as `ComfyUI_RS_MultiCharacter_Sampler` / `Anima (local)`, `SDXL (local)`, `Krea2 (local)` or `MOSS-Image (local)`. Similar field names provide caption interoperability; this is not a claim that NAI produced the image or can reproduce local sampling.

## Restoration boundary

The image loader returns original character texts and centers, common text and prompt syntax in the dedicated pipe. Imported NAI syntax is converted for ComfyUI only when encoding; the original text remains available for saving. Positive and negative character rows must have matching single centers. Missing, malformed, oversized, nonfinite and unsupported-version metadata fails with an error.

`use_image_settings` restores local settings only when the local versioned object is present. Connected model/CLIP/VAE/LoRA are never replaced. The metadata contains filenames, not weights or content hashes, so a changed model file with the same name is not detected. Exact replay also depends on the runtime and hardware.

Character negative strings can be stored and read, but the regional sampler rejects them before generation because per-character negative attention is not implemented. EXIF orientation that changes the coordinate system is rejected. Metadata decoding is data-only; it does not execute workflow nodes or fetch models.

## Local detailer

`RSMultiCharacterDetailer` consumes the same dedicated `character_pipe` from the sampler or image loader, an IMAGE, and the caller's MODEL/CLIP/VAE. It uses ordinary local masked img2img for each crop, with common text plus one matched character's original positive/negative text. It does not install the full-frame regional attention patch on a face crop. Sampler character-negative restrictions above apply to full-frame generation; the detailer can encode one matched character's negative text normally.

`RSMultiCharacterDetectionLoader` returns a separate detection bundle. SEGM takes priority and skips BBOX and SAM loading. With SEGM OFF, BBOX returns rectangles or SAM-refined masks. OFF models are neither downloaded nor loaded. Catalog downloads verify size and SHA-256 before atomic installation into the existing Impact model folders. `RSMultiCharacterTaggerLoader` exposes three revision-pinned choices and keeps download progress separate from saved widget values. No NovelAI extension or API is needed.

The detector constructs full-image masks, repairs small holes/notches, dilates and assigns disjoint ownership. Matching uses crops of the immutable original image and chooses only an original character ID. Literal tag vocabulary phrases such as `black hair` inside `short black hair` can be recognized without rewriting the original prompt. Low scores/margins preserve a region; high-confidence mistakes remain possible. Matching is independent per region, allowing multiple eye/hand regions for one character. XY values remain in the pipe and metadata but do not override visual matching.

Each correction starts from the original image, encodes 4D image latents or Anima's 5D single-frame latent, and supplies a noise mask to `common_ksampler`. Feathering stays inside the ownership mask. Pixels outside every edited mask remain unchanged in the IMAGE tensor and lossless saves. A report exposes region boxes, character IDs, scores, skip reasons and actual prompt/seed/sample size.

Autosave appends `rs_multicharacter.detail_history` with correction settings, assets and report. Original generation settings remain in `settings`; detailer crop settings never overwrite them. PNG and WebP carry the same original captions and local history, without a workflow graph. The output pipe carries the enriched record for another pass. A pipe without original local settings can be detailed and saved, but cannot restore nonexistent T2I settings through `use_image_settings`.
