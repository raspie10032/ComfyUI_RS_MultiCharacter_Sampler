# 0.1.2 Beta

This release brings the validated development branches into one package: all installed sampler/scheduler choices, local character detailing, and SDXL, Krea 2 and MOSS generation. The package version is `0.1.2`; the development status and user-facing labels are Beta.

## Included changes

| Change | Implementation commit | Evidence |
| --- | --- | --- |
| Host sampler/scheduler inventory and Anima starting points | `f091f09` | [405-combination comparison](sampler-combinations.md) |
| Local detailer, combined detection loader and character tagger loader | `1bb8c79` | [Anima detailer validation](detailer-validation.md) |
| SDXL regional generation and checkpoint-loader example | `0020080` | [SDXL validation](sdxl-validation.md) |
| Krea 2 Turbo / MOSS-Image SFT generation, adjustable steps and current Anima compatibility | `1011680` | [Krea 2 / MOSS validation](krea-moss-validation.md) |

There are six nodes: character prompts, sampler, image loader, detailer, detection loader and tagger loader. English, Korean and Japanese instructions and node labels accompany the examples.

## Models and validation boundaries

| Model family | Actual generation evidence | Remaining limits |
| --- | --- | --- |
| Anima | Earlier 1–6-character trials, the 405-combination comparison, local detailer runs and a regression on the newer ComfyUI checkout | Character counts and matching can fail; sampler execution success does not establish image quality. |
| SDXL | 35 generations with Illustrious XL v1.0 / NoobAI XL 1.1, including caption swaps and XY layouts; a later Illustrious regression | Count/identity failures remain, especially in dense layouts. Other derivatives and SDXL detailing are unverified. |
| Krea 2 Turbo FP8 | Five generations: two characters, caption swap, three characters, four-character XY and metadata replay | T2I only; base variants, other quantizations, reference editing and detailing are unverified. |
| MOSS-Image SFT BF16 | The same five cases, including metadata replay | Some requested props and eye colors were missed. Other variants, reference editing and detailing are unverified. |

SD1.5 is not supported in this release. A small random-weight routing probe is not a real-checkpoint generation test. Flux, SDXL Refiner/inpainting models, ControlNet and additional attention overrides are also outside the supported sampler paths.

## Updating and compatibility

Update the existing installation through ComfyUI-Manager or Git, then restart ComfyUI when its queue is idle. Krea 2 and MOSS require a ComfyUI build with their native model and text-encoder support; see their validation document for the tested checkout and exact assets. Updating this extension does not update ComfyUI or download generation weights.

For the optional detailer, install Impact Pack, Impact Subpack and `requirements-detailer.txt` in the ComfyUI Python environment. The detector/tagger loaders display download progress for selected missing catalog models. Start with the [Anima detailer example](../examples/two-characters-detailer-anima.json).

Existing node IDs, pipe types, widget ordering and Anima defaults are retained. Display names now say Beta. The metadata schema remains version 1, and the existing `*-spatial-alpha-1` engine identifiers remain valid format identifiers; the release label does not rename them. Autosave still records generation metadata without embedding a ComfyUI workflow. Character negatives remain unsupported by the regional sampler; use its common negative prompt.

## Release checks

Run from the extension directory using the tested ComfyUI Python environment:

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -q
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
comfy node validate
git diff --check
```

The optional native tests run small CPU models to check interface behavior. Full-model generation evidence is recorded in the linked reports. Version and label changes do not establish additional image-quality coverage or resident-installation validation.

The 0.1.2 release candidate passed all **69 Python tests**, including the optional native CPU integrations, both JavaScript checks, `comfy node validate` without warnings, and `git diff --check`. Version/display-label consistency, example JSON, local documentation links and inclusion of all four implementation commits were also checked. Registry validation flagged semicolon-separated statements in four test files; splitting those statements preserved their Python ASTs and the tests passed again.
