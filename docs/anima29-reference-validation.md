# Anima 2.9B reference support validation — 2026-10-29

The public sampler now accepts both 28-block Anima 2B and 40-block Anima 2.9B for `reference_frame`. The user chooses the checkpoint. The sampler chooses and verifies the matching frame adapter. No runtime monkeypatch, `--fast` option, or experimental layer skip is used in this validation.

`role_kv` remains available for the 28-block 2B model only: its current weights were trained for that architecture. Selecting it on 2.9B produces an actionable error recommending `reference_frame`, before downloading that incompatible adapter. This is not a rejection of the 2.9B checkpoint.

## Implementation

- The converted 2.9B adapter maps the existing 28 adapter blocks onto their correct positions in the expanded 40-block model; all 40 model blocks execute. The inserted 12 blocks have no frame adapter delta, not a skipped forward.
- Validate every required down/up/alpha tensor before applying any hook. Reject wrong block counts, missing layers, nonfinite tensors, missing/malformed/zero rank and incompatible dimensions with an understandable error.
- Reuse a previously downloaded valid adapter after SHA-256 validation. Download a first copy through the Hugging Face downloader with progress reporting and a pinned revision, then verify SHA-256. Hugging Face manages transfer locks and resumable files. Corrupt copies are rejected and preserved for user replacement; network failures explain how to queue again to retry/resume.
- Existing workflows default to `reference_frame`; 2B `reference_frame` and `role_kv` remain available. Model choice stays in the checkpoint loader.

## Actual generation conditions

RTX 4070 Ti SUPER, BF16; 1152×896; 30 steps; CFG 4.5; Euler ancestral / SGM uniform. Two adult women in a cafe, generic prompts without character names. Two reference images, each longest edge 768 px; reference strength 0.8, frame adapter strength 1.0. Each paired A/B and B/A run uses the same seed. Mask and progressive cases use their separately recorded seeds, so they are not controlled quality comparisons against A/B.

The overlap case uses two painted silhouettes with overlapping support. The final preview follows the RegionMask serialization format used by the public node. An initial validation script packed bits in the wrong order; its files were preserved in `support-29-mask-initial-bitorder`, and the mask case was rerun after correcting the script. This was a validation harness correction, not a product mask decoding change.

Style cases use `anima/RSCV5_Anima-final42330-comfy.safetensors` and `anima_MyMyArtStyleLoRA.safetensors` on different character slots, model strength 0.7, CLIP strength 0. These existing 2B-trained style LoRAs test normal/precision execution and restoration on 2.9B. They are not a guarantee of identical style transfer to an expanded checkpoint; 2.9B-specific training/conversion was not evaluated. The progressive case starts at 0.75 scale with Lanczos resizing and ends at 1152×896.

Each figure is a single-seed operational check, not a preference study. Model loading and downloads precede the timed region; the table includes sampling and image decode/encode work in the node call. Peak allocated/reserved values come from PyTorch; board peaks are nvidia-smi samples and can include other allocations on that GPU. Times are not a same-condition model-family benchmark.

## Actual results

| Model / case | Seconds including encode/decode | Peak allocated MiB | Peak reserved MiB | Board peak MiB (250 ms samples) |
|---|---:|---:|---:|---:|
| 2.9B / `no-reference-before` | 18.19 | 8252 | 8896 | 9215 |
| 2.9B / `frame-ab` | 108.03 | 8253 | 9196 | 9515 |
| 2.9B / `frame-ba` | 108.17 | 8253 | 9196 | 9515 |
| 2.9B / `frame-masks-overlap` | 109.89 | 8252 | 9210 | 9529 |
| 2.9B / `frame-style-normal` | 154.76 | 8335 | 9372 | 9691 |
| 2.9B / `frame-style-precision` | 358.96 | 8352 | 9390 | 9709 |
| 2.9B / `frame-progressive` | 85.75 | 8251 | 9612 | 9363 |
| 2.9B / `no-reference-after` | 17.76 | 8252 | 9160 | 9479 |
| 2B / `no-reference-before` | 13.15 | 6656 | 7304 | 6677 |
| 2B / `frame-ab` | 80.30 | 6657 | 7604 | 7923 |
| 2B / `role-ab` | 23.60 | 7074 | 8830 | 9149 |
| 2B / `no-reference-after` | 12.50 | 6656 | 7556 | 7875 |

A/B→B/A changes the principal hairstyle and ornament to the opposite character. Mask and overlap output remains two distinguishable people, with weaker accessory fidelity than simple boxes. Clothing color/detail can vary or leak; separation is useful but not perfect identity reproduction. Style, precision and progressive cases are operational smoke checks, not proofs that quality always improves.

For both model depths, no-reference images before and after reference tests are pixel-identical. Every individual generation checks finite latents/pixels and equality of hook counts before and after execution. Frame audit confirms 40 model blocks with 28 adapter blocks on 2.9B, and 28/28 on 2B. Reference K/V and hooks are restored after execution.

## Automated checks

- Python unittest discovery: **343 tests run, 341 passed, 2 skipped**. Skips are the optional upstream RoPE comparison and a legacy no-native-bypass path not applicable to this installed core.
- JavaScript: **15 UI test files passed**.
- CPU coverage includes 28↔40 mapping, rejection and cleanup on malformed adapters, auto selection, checksum reuse, retry after a failed call, progress readiness, cancellation propagation, and unsupported depth before weight file access.

## Evidence and reproduction

Local experiment root: `/var/home/raspie/Documents/Codex/RS_Anima_ElectronGirl_compare_20261029`.

- `run_support.py`: public sampler/pipe setup and generation harness.
- `support-29/` and `support-base/`: per-case PNG with experiment metadata, JSON routing audit, nvidia-smi samples and event log.
- `support-29.log`, `support-base.log`, `support-mask-corrected.log`: real generation output.
- `support-python-tests.log`, `support-ui-tests.json`: full automated check results.
- `support-29/cases-preview.jpg`: selected 2.9B cases; `support-29/frame-masks-overlay.png`: mask support over the generated result.

```bash
cd /var/home/raspie/Documents/Codex/RS_Anima_ElectronGirl_compare_20261029
CUDA_VISIBLE_DEVICES=GPU-c8460706-b04f-d00d-2a88-b036f96fc417 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /home/raspie/AI/ComfyUI/.venv/bin/python run_support.py --model 29 --cases no-reference-before,frame-ab,frame-ba,frame-masks-overlap,frame-style-normal,frame-style-precision,frame-progressive,no-reference-after
CUDA_VISIBLE_DEVICES=GPU-c8460706-b04f-d00d-2a88-b036f96fc417 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /home/raspie/AI/ComfyUI/.venv/bin/python run_support.py --model base --cases no-reference-before,frame-ab,role-ab,no-reference-after
cd /var/home/raspie/Documents/Codex/RS_Anima_RoleRefKV_integration_20261028/source
/home/raspie/AI/ComfyUI/.venv/bin/python -m unittest discover -s tests -v
for test in tests/*_ui.cjs; do CAMERA_PYTHON=/home/raspie/AI/ComfyUI/.venv/bin/python node "$test" || exit 1; done
```

The runner expects the downloaded model, existing reference images and style LoRA files recorded above; GPU UUID is specific to this workstation. Do not start duplicate GPU runs while the verified validation process is alive.

## Sources and scope

- https://github.com/ElectronGirl/ComfyUI-Anima-Ref-Adapter
- https://huggingface.co/Gazingstars123/Anima-2.9B
- https://huggingface.co/pamparamm/anima-ref-adapter-2.9B-converted

Original source attribution and the reason for the 2.9B mapping remain in the user-facing reference guide. These changes are committed to the development branch. A GitHub main merge, Registry release and everyday ComfyUI installation update are separate deployment steps and are not claimed by this report.
