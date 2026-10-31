# RS Workspace 1.1.0 validation — 2026-10-31

## Scope

RS Workspace assembles the existing public nodes. This document separates automated routing checks, actual model execution and interactive browser evidence. Timing below is whole-request time and may include model loading; it is not a speed benchmark.

## Existing actual generation evidence

| Model family | Steps | Size | Whole request | Outcome |
| --- | ---: | --- | ---: | --- |
| SDXL | 30 | 1024×1024 | 24.03 s | success |
| SD1.5 | 30 | 1024×1024 | 18.03 s | success |
| Anima 2.9B | 30 | 1024×1024 | 39.28 s | success |
| FLUX.2 Klein 4B | 4 | 1024×1024 | 33.03 s | success |
| FLUX.1 Schnell | 4 | 1024×1024 | 45.03 s | success |
| FLUX 3 | 16 | 1024×1024 | 24.03 s | success |
| Krea 2 | 8 | 1024×1024 | 60.04 s | success |
| MOSS | 50 | 1024×1024 | 60.04 s | success |

These are individual execution checks of generated app routes, not a full visual quality matrix. An additional Anima 2B request with 3D pose, painted masks, camera, interaction and face detailing succeeded: two detected faces, two matched/detailed characters, zero preserved faces, about 49.07 s total.

## Interactive verification

- Chrome: actual 3D mannequin rendering, Wave pose, joint selection, camera orbit and Apply to node; Anima ↔ MOSS routing and per-model sampling restoration; existing unsaved workflow retained in a separate tab.
- Chrome: two app-button generations completed with seeds 0 and 420934239660504. Results showed two characters and the requested differing hair/clothes. Refresh restored the pose, camera, model selection and result list.
- Firefox: wildcard search/insertion, seeded preview and missing-file errors. Anima camera + face-detail generation completed in about 36.98 s, with two faces detected and detailed. The actual resolved prompts reached camera and detailer.
- Firefox: opening the original workflow PNG restored the app, model, source wildcard templates and last resolved prompts. The PNG contains 21 nodes and both `workflow` and `prompt` metadata.

The browser runs above were recorded during app and wildcard development on 2026-10-31. Release-only changes add documentation, a version bump, wildcard CI coverage and output-prefix restoration; they do not claim an additional browser run.

## Release checks

- Python suite with the installed native ComfyUI and GGUF paths: **421 tests, 414 passed, 7 skipped**. Exclusions are two optional upstream-source comparisons, one old-core fallback test (current core provides native bypass), and four explicit isolated CUDA/xformers tests.
- JavaScript: **19 test files passed**. The suite covers app routing/settings, inactive dependencies, wildcard resolution and recovery, seed callbacks, editor controls and existing UI behavior. 
- Real installed node definitions were used for **98 typed request closures across 24 installed model entries** during development. These are structural checks, not 98 actual generations.
- New reopening regression: a customized output filename prefix survives app initialization.

## Reproduction

Run Python with the actual ComfyUI environment rather than a Python without its dependencies:

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI \
RS_MC_TEST_GGUF=/path/to/ComfyUI/custom_nodes/ComfyUI-GGUF \
/path/to/ComfyUI/.venv/bin/python -m unittest discover -s tests -v
node tests/test_app_graph.cjs
node tests/test_app_wildcards.cjs
```

The optional CUDA/xformers tests require their separate isolated setup. For interactive checks, follow the install/open guide, generate an image, switch models and return, then reload the saved PNG and confirm both original templates and resolved prompts.

## Remaining limits

The app catalog handles safetensors; GGUF loader selection and arbitrary encoder filenames need manual node workflows. Korean app labels, one request per Generate click, and the documented pose/reference/progressive combination restrictions remain. Manual point, box and mask layout and all existing graph nodes remain usable. No claim is made that every feature combination or model has equal image quality.
