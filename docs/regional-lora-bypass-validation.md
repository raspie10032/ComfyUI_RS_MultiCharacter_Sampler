# Zeta: Anima small-factor LoRA validation — 2026-10-17

> Correction in **0.1.7 Zeta Fix**: the default dynamic-VRAM completion check below
> did not prove that the LoRA reached the inference model. ComfyUI may replace that
> model after preparation. Version 0.1.6 attached bypass to the old modules and could
> generate exactly the no-LoRA image. The timed paired tests explicitly disabled
> dynamic VRAM; their scope must not be extended to default dynamic execution.
> See [the fix and controlled dynamic-VRAM comparisons](release-0.1.7.md).

This changes only the application of eligible Anima LoRA weights. Character
conditioning, coordinate/box masks, CFG and the number of predictions stay the same.
ComfyUI's native Bypass LoRA evaluates the base layer plus the two small factor
multiplications. Other formats keep the existing low-memory weight-hook path.

## Controlled generation comparison

Anima Base v1.0 BF16; Qwen 3 0.6B text encoder; Qwen Image VAE; two adult characters
in a campus garden. 1024×768, seed 250917, 30 steps, CFG 4, Euler ancestral / SGM
uniform. Character 1 uses RSC and character 2 uses MyMy; model strength 1.0, CLIP
strength 0.0. Each file contains 280 ordinary Linear rank-32 LoRA patches.

ComfyUI `5cc4b870094c89090db54bd8d12649dcaf89f2ba` (`v0.41.0-11`), RTX 5060 Ti
16 GiB, CUDA logical device 0 mapped with `--cuda-device 1`. A private server uses
the candidate source. Production installation and published main are separate.
The paired runs use `--disable-dynamic-vram`; the default dynamic mode was tested
separately. Measurements include the sampler node, its encoding and VAE decoding,
exclude queue polling, and synchronize CUDA at both ends. Model loading is warmed
for the paired comparison. Generation order is hooks, bypass, hooks, bypass.

| Backend/run | Seconds | Weight synthesis calls | Predictions | Peak allocated VRAM GiB | Sampled process RSS GiB |
|---|---:|---:|---:|---:|---:|
| Weight hooks 1 | 155.69 | 16,800 | 60 | 6.197 | 8.305 |
| Small factors 1 | 65.86 | 0 | 60 | 6.197 | 6.633 |
| Weight hooks 2 | 150.34 | 16,800 | 60 | 6.197 | 8.485 |
| Small factors 2 | 65.79 | 0 | 60 | 6.197 | 6.634 |

The mean time falls from 153.02 to 65.82 seconds: 2.32× throughput, 57.0% less time
for this condition. RSS is a ~3-second sample of the server process, not a measured
instantaneous peak or independent cold-start trial. PyTorch peak allocated VRAM
includes the model and VAE; a VAE peak can hide changes during denoising. No claim
is made that total VRAM falls by the factor-storage ratio.

The two original factor sets total **175 MiB**. A hypothetical cache of their
fully merged target weights would use **6.56 GiB**, excluding base weights,
backups and temporary data. The old `MinVram` path already avoided that cache;
the change removes repeated weight synthesis without enabling a large cache.
CPU file tensors and transient compute-device factor copies can coexist.

## Image and state checks

- Old versus new full generation: RGB mean absolute difference **5.0086/255**,
  RMSE 12.0608 and PSNR 26.503 dB. Two people, hair/clothing distinctions and the
  shared background remain visually similar in the inspected pair. One seed and
  prompt do not establish equivalent quality or character fidelity generally.
- Each backend repeated with the same inputs gives pixel-identical results.
- No-LoRA baseline, selected files at model/CLIP strength zero, and subsequent
  no-LoRA generation are pixel-identical. Temporary LoRA effects do not persist.
- Swapping regional file assignments changes the result (RGB MAE 35.1333).
- One file at two strengths produces one shared 87.5 MiB factor set and 60
  predictions, rather than duplicating the factors for each strength.
- A global model LoRA at 0.25 plus two regional LoRAs completes with both backends
  in a 512×512 / 4-step smoke test. It checks composition, not final image quality.
- Default ComfyUI dynamic VRAM mode completes the 1024×768 / 30-step request.
- The detailer detects and matches two faces, then edits both with their selected
  LoRA through bypass (16 steps per crop, denoise 0.25). Its measured node execution
  is 13.33 seconds, 16 predictions for each LoRA, zero weight synthesis calls,
  and successful cleanup. Detector/tagger loading is upstream of that node and
  excluded from this timing. This is a functional check, not an old/new speed pair.
- Native CPU tests compare positive, negative and zero strengths against merged
  FP32 weights, and check model immutability, exact dispatch restoration after
  executor failure or partial injection, and factor release after an error.
- Every successful measured bypass run checks that factor-device copies have
  been released and temporary `forward` attributes have been removed.

## Compatibility and scope

All patches in a file must qualify. Non-Anima models, cores without native bypass,
DoRA and other adapter types, diff/offset/reshape/convolution patches, quantized
layers, custom forced dispatch and multi-GPU clones use existing weight hooks.
Unsupported fast-path shapes fall back as a complete file; no partial LoRA is
silently applied. Invalid model-family files keep their existing error handling.
The CLIP path is unchanged. Anima precomputed text-adapter patches remain rejected
for regional use and should be connected globally.

Current-core Python: **106 tests passed**. Old ComfyUI v0.3.76: **100 test entries,
8 skipped** for unavailable features, no failures. All four JavaScript UI suites
passed. This fast path's completed image evidence is Anima; other families retain
the earlier backend, not a newly verified factor-only implementation.

No new UI controls or workflow fields are required. Metadata saves filenames and
strengths, not a promise of pixel-identical reproduction across backend changes.

## Reproduction and evidence

The local validation bundle is `RS_MC_zeta_bypass_20261017/validation` under the
workspace's Codex folder. Each run retains its `.api.json`, server receipt/history,
output PNG, routing audit, resource samples and `.benchmark.json`. `summary.json`
and `index.html` compare completed runs. `scripts/run_cases.py` resumes a known
receipt instead of blindly resubmitting a prompt. `scripts/analyze.py` produces
pixel comparisons and the visual comparison page.

The private benchmark uses the same production node for both backends, forcing
`prepare_bypass` to return no plan only in the old-path run. It counts native weight
synthesis calls, measures CUDA memory, and verifies cleanup. These instrumentation
nodes are outside the repository and are not distributed.

An initial measurement attempt used a mock that retained inference tensor arguments
and inflated memory; those results are excluded and retained in
`instrumentation-failure/`. The corrected counter stores integers and plan metadata
only. A detailer request sent before its private benchmark class was reloaded was
rejected by validation without executing; it was rerun after the isolated server
loaded that class. Neither failure is presented as a product benchmark.
