# ComfyUI compatibility review — 2026-10-17

This change fixes SDXL use on ComfyUI versions predating Anima, while retaining
the 0.1.2 node inputs, outputs, metadata format and generation settings.
It does not add architectures or merge the deferred detail-conditioning experiment.

## Reproduced faults and changes

1. `RSMultiCharacterSampler.generate()` unconditionally imported Anima and its
   routing implementation before selecting the model family. Release `5689176`
   failed with `ImportError: cannot import name 'Anima'` on ComfyUI `v0.3.76`, even
   when the connected model was SDXL. Architecture checks now tolerate absent
   optional classes and import the Anima engine only for Anima.
2. SDXL's existing 4-channel, H/8 × W/8 latent was passed through
   `fix_empty_latent_channels(..., downscale_ratio_spacial=8)`. The older API does
   not accept that keyword. SDXL now calls the native helper without the ratio
   hint; the newer architectures retain the hint for their different latent
   layouts. The host helper remains responsible for its latent normalization.
3. The native Krea test imported the MOSS implementation too, incorrectly failing
   on a ComfyUI checkout that supported Krea but not MOSS. Tests now import and
   skip each absent architecture independently.

The new SDXL CPU integration exercises the public node through real ComfyUI
model wrapping, a small native SDXL UNet, sampler, scheduler and attention
routing. It checks finite outputs, latent shape, preserved character text,
active routing and forward restoration. CLIP/VAE are synthetic and weights are
random: this test establishes API integration, **not image quality**.

## Verified snapshots

| ComfyUI snapshot | Native CPU coverage | Python suite |
| --- | --- | --- |
| `v0.3.76` | SDXL | 67 passed, 3 architecture tests explicitly skipped |
| `15eb748` — currently installed Linux source | Anima, SDXL, Krea 2 | 69 passed, MOSS explicitly skipped |
| `5cc4b870094c89090db54bd8d12649dcaf89f2ba` — current upstream snapshot | Anima, SDXL, Krea 2, MOSS | 70 passed |

All suites used Python 3.12.14 / PyTorch 2.14.0+cu130 on Linux with native model
integration tests forced to CPU. The newest snapshot's required kitchen/aimdo
packages were isolated from the everyday ComfyUI environment. The checks for
character UI serialization and detailer/loader UI passed separately. All six
node schemas (input order/defaults, outputs and execution method) matched the
0.1.2 baseline exactly in the installed host environment.

This is a set of tested snapshots, not certification of every intervening
ComfyUI version. Selecting Anima/Krea/MOSS still requires a host that implements
that architecture. SD1.5, arbitrary model patches and ControlNet remain outside
the supported regional sampler contract. No Windows GPU run was performed.

## Real checkpoint generation

Illustrious XL v1.0 was also loaded on an RTX 4070 Ti SUPER with upstream
`5cc4b87`: 768×512, 12 steps, CFG 5.5, Euler ancestral / normal, seed 617201,
common prior 0.3, character gain 1.3 and separation 0.5. Both original and fixed
code completed sampling and VAE decoding with finite output and restored routing
forwards. This low-step smoke test is not a two-character composition benchmark.

The first baseline invocation and its repeated invocation produced different
pixels even with the unchanged release code. After this initial invocation,
the repeated release and candidate latents/decoded pixels matched exactly, as
did two consecutive candidate runs. This observation is preserved in the local
`gpu-smoke-repeated.json`; it is not presented as universal determinism or
attributed to the compatibility fix. A fresh process running the final candidate
also reproduced the first baseline image exactly (pixel SHA-256
`b8a47416e715bb0cd7cae7749f39a0af77a4e507b93477e900ff19c9400cebf2`).
Thus matching cold runs and matching warmed runs show no output change from
the compatibility patch in this checkpoint case.

## Detailer evidence and automated coverage

The three READMEs previously said only Anima detailing was tested. The retained
SDXL/Krea/MOSS executions have now been checked against their saved result and
mask hashes and documented in [the detailer report](detailer-validation.md#subsequent-012-model-compatibility-smoke-checks).
No new detailer algorithm was introduced.

[The test workflow](../.github/workflows/tests.yml) runs CPU checks on Linux with
`v0.3.76` and the pinned current snapshot, plus Windows with that current
snapshot. It uses no checkpoint downloads, GPU or service credentials. It is
prepared in this branch; remote GitHub Actions/Windows execution has not been
claimed. Pinning the upstream revision makes failures reproducible; update that
revision deliberately when reviewing a new ComfyUI release.

To repeat the source/API tests with a locally provisioned ComfyUI environment:

```bash
RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -v
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
```

Omitting `RS_MC_TEST_COMFYUI` deliberately skips native integration tests. A
passing offline-only suite therefore does not prove native model compatibility.
Full local logs and generated smoke images are retained in
`RS_MC_compatibility/validation` beside the source checkout.
