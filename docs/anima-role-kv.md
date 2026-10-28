# Anima Role K/V: experimental regional image references

The purpose is **regional attention control**: the image tokens belonging to
character A read reference A's K/V, while character B's tokens read reference B.
Reference identity, action fidelity and isolation in the resulting image are not
guaranteed. The shared image state still couples adjacent regions.

## Connect and download

1. Use Anima Base v1.0 in native BF16 or FP32 and the usual CLIP/VAE loaders.
2. Feed each ordinary Load Image output to an **Image Reference** node. Match its
   character number to Prompt, Position/Mask and optional character LoRA.
3. Choose **Anima reference method → role_kv** on all enabled reference inputs.
   Building-node order remains free. Finalize into the ordinary RS sampler or
   the RS progressive sampler. No extra MODEL adapter node is needed.
4. Queue generation. The dedicated adapter is downloaded on first use, showing
   status through the existing node download-progress system. It is about
   **504 MiB / 528,546,184 bytes**. OFF/strength 0 performs no Role K/V loading.

Install `requirements-reference.txt` with ComfyUI's Python. The fixed upstream
revision and SHA-256 are in `reference_assets.json`. Existing matching files in
configured model/LoRA folders are reused. The managed location is
`models/ipadapter/rs_reference/anima_role_kv/comfy/anima-role-ref-kv-v1.0.safetensors`.
A failed download can be retried; a checksum mismatch names the file to replace.
The adapter is applied internally at 1.0. Do not also apply it via a LoRA loader.

The common Reference node and the legacy Anima Character Reference alias both
have the optional method selector. Existing workflow widget order is unchanged;
missing method values retain `reference_frame`. Existing global reference-frame
MODEL adapter nodes cannot be combined with Role K/V.

## What is controlled

- Independent reference VAE encodings and per-block K/V banks for each active
  character; the selected longest edge is retained and aligned to the VAE grid.
- Points use the usual ownership partition. Explicit boxes and silhouettes use
  their spatial membership; overlapping tokens may read both owning banks.
- Uncovered background tokens read no reference bank. Negative CFG branches
  read no reference bank. Generated image tokens can still see one another.
- Sampling completion, interruption and failure release invocation-local banks.
  A changed progressive target grid rebuilds banks and RoPE for that grid.
- Character prompts still enter spatial cross-attention, but this adapter uses a
  **balanced profile** rather than RS's strong isolation/strength schedules.
  The original strong profile collapsed the experimental images.

## Limits and compatibility

This is an opt-in experiment; the existing reference-frame backend remains the
default. The mode is Anima-only; SD1.5, SDXL, MOSS, FLUX and Krea retain their
existing reference implementations. Quantized Anima variants are rejected.
Character LoRAs currently require **Normal** application; Precision or an
unsupported adapter that falls back to Precision raises an actionable error.
Global ordinary style LoRAs remain possible, subject to model compatibility.

The interaction preset must be `baseline`; extra boundary-separation presets
are rejected rather than silently ignored.

Body-part-name guidance is not supported in this backend; set its strength to
0 (the silhouette mask can still be used). Text regions still use their box
conditioning; text correctness is not guaranteed. The detailer continues its
existing prompt/LoRA behavior and ignores image references. Native KSampler and
external attention/control patches are outside this backend's support.

Metadata records the reference method and audit, but never embeds reference
pixels. Reconnect source images after restoring saved generation metadata.
Strong references can copy clothing/poses or override requested attributes;
separate caches alone do not guarantee different actions or prevent all mixing.

## Integration validation: 2026-10-29 KST

Public RS node methods were exercised on a 4070 Ti SUPER, Anima Base v1.0,
1152×896, 30 steps, CFG 4.5, Euler ancestral / SGM uniform. Two full reference
images used a 768px longest edge and strength 0.8. The shared cafe prompt named
no reference identity, hair color or clothing color. Character captions were
`1girl, adult woman, smiling, holding a ceramic cup`. Adapter strength was internally 1.0.

The first batch covered reference A/B, B/A, overlapping boxes, different
per-character style LoRAs in Normal mode, progressive sampling and repeated
reference-free calls. A final batch additionally covered silhouette masks and
a genuine before→references→after reference-free comparison.

Final-batch elapsed times include the sampler call and VAE decode, not original
model loading or file download: A/B **24.40s**, overlapping boxes **25.14s**,
silhouette masks **24.73s**, progressive sampling starting at 0.75 **20.22s**.
These are single runs, not a general speed guarantee. The original reference-free
image and the image after all reference jobs were **pixel-identical**.

Visual inspection confirmed that swapping references swaps prominent hair and
accessory cues. Clothing colors are weaker: even the ordinary A/B run changed
the right reference's yellow garment into cream. Per-character styles can weaken
reference clothing further. The overlap/mask tests prove execution and ownership
routing, not complete visual identity isolation. Earlier research also failed a
left-cup/right-book action assignment; the integration does not claim to fix it.

Separate CPU tests numerically cover exclusive/overlap/background bank access,
zero reference strength, negative CFG exclusion, point partitions, exception
cleanup, widget compatibility and downloader retry/integrity behavior. Node
help and locale checks cover Korean, Japanese, Simplified/Traditional Chinese.

## Sources

https://arca.live/b/aiart/187357665

https://huggingface.co/AnticPan/Anima-Role-Ref-KV

The independent one-capture experiment at
https://arca.live/b/aiart/187358922 is related research; Spectrum acceleration
from that experiment is **not included** in this integration.
