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

The additional `rs_multicharacter` object stores schema `version: 1`, engine `anima-spatial-alpha-1`, prompt syntax, sampler/routing settings, effective centers, slot count and connected loader descriptions. Known standard model, text encoder, VAE and LoRA loaders are recorded by filename and settings. Unrecognized loader chains are explicitly marked unresolved. No credentials, arbitrary graph nodes, absolute model directories or weight files are serialized.

The extension identifies output as `ComfyUI_RS_MultiCharacter_Sampler` / `Anima (local)`. Similar field names provide caption interoperability; this is not a claim that NAI produced the image or can reproduce local sampling.

## Restoration boundary

The image loader returns original character texts and centers, common text and prompt syntax in the dedicated pipe. Imported NAI syntax is converted for ComfyUI only when encoding; the original text remains available for saving. Positive and negative character rows must have matching single centers. Missing, malformed, oversized, nonfinite and unsupported-version metadata fails with an error.

`use_image_settings` restores local settings only when the local versioned object is present. Connected model/CLIP/VAE/LoRA are never replaced. The metadata contains filenames, not weights or content hashes, so a changed model file with the same name is not detected. Exact replay also depends on the runtime and hardware.

Character negative strings can be stored and read, but this alpha rejects them before generation because per-character negative attention is not implemented. EXIF orientation that changes the coordinate system is rejected. Metadata decoding is data-only; it does not execute workflow nodes or fetch models.
