# 1.0.0 Hangeul (한글)

OpenPose JSON can now create numbered person masks for the existing regional generation pipe. This is a composition tool: **the model receives text in regions, not an OpenPose skeleton image**. No pose detector, ControlNet or additional pose weights are downloaded.

## Changes

- `RS OpenPose Masks (Experimental)`: load a JSON file, paste one frame, or connect a `POSE_KEYPOINT` frame. COCO-18 and BODY-25 pixel coordinates are accepted. Array order maps to the existing character row numbers.
- Thickness adjusts limb width and body padding. Character Position moves/scales the person mask and its body-part regions together. Canvas overflow is clipped.
- The diagram updates directly for pasted JSON. Connected inputs use the executed result; changing an upstream source clears the stale diagram and asks for another execution. Unconnected thickness/confidence controls remain editable after execution. Intermediate-output replay restores the preview even when generation is already cached after reloading a graph.
- Optional **very weak attention guidance using the names of skeleton parts** places `head`, `hands`, `chest`, `thighs`, `legs`, `feet` in mapped areas. Default strength is **0 / OFF**. This path supports Anima and SDXL.
- `RS Character Interaction`: baseline, delay3, delay6 and custom presets can retain separation longer only in non-overlapping character regions. Overlap and background retain the ordinary schedule. Additional separation supports Anima/SDXL and experimental SD1.5; unsupported families raise an explicit error.
- PNG/WebP generation metadata preserves placed masks, body-part settings and interaction settings. Reloaded masks retain the same placement; replacing a mask clears its previous body-part regions.
- Korean/Japanese node labels and control descriptions, English documentation, an external-pose example and regression coverage are included.

## Validation and its limits

The final local source suite ran 204 Python tests against ComfyUI 0.41.0: 203 passed, one legacy bypass test skipped because this core provides native bypass. All 10 JavaScript UI suites passed. These include synthetic CPU model integrations and are not image-quality evidence.

The release validation also used an external two-person front-hug OpenPose frame, with its upstream URL, SHA256 and MIT license retained in [the example](../examples/openpose/README.md). Actual Anima generations exercised masks with guidance OFF/ON, transformed overlapping masks and metadata replay. An SDXL generation and the ComfyUI execution button were also exercised. Connected-JSON UI checks exercised drag, scale, thickness edits, upstream invalidation and graph reload. Placed masks and body-part guidance restored from a generated PNG reproduced identical pixels. These trials prove the tested execution paths; they do not establish pose accuracy or quality across all seeds and model families.

Earlier SDXL 20 OFF / 20 ON comparisons did not improve high-five success. Body-part names can change clothing or weaken character appearance. Masks guide approximate composition; exact joint angles, hand contact, anatomy and identity are not guaranteed. Existing support for other model families does not imply that the new experimental body-part guidance supports those families.

Reproduce the automated checks from the repository root:

```bash
RS_MC_TEST_COMFYUI=/path/to/ComfyUI OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -v
node tests/test_pose_masks_ui.cjs
node tests/test_builder_ui.cjs
node tests/test_position_editor_ui.cjs
```

Load [anima-hug.json](../examples/openpose/anima-hug.json), select your installed model/CLIP/VAE, and generate with Euler ancestral / SGM uniform. The example starts with body-part guidance OFF. [Usage, supported inputs and limits](openpose-mask-guides.md).

## Connected-input preview completion

Connected POSE_KEYPOINT and STRING JSON inputs publish a bounded raster preview after execution. Character Position uses that result directly; changing local thickness rebuilds the diagram from the executed pose. Changing the upstream node values or output link invalidates the old preview and asks for another run. A reloaded workflow can also recover the intermediate preview from ComfyUI's execution cache (`HAS_INTERMEDIATE_OUTPUT`); preview recovery does not force another image generation.

Final local checks: 204 Python tests ran, 203 passed and one existing core-dependent test was skipped; all 10 JavaScript test files passed. Real browser checks covered linked STRING JSON, dragging/resizing the mask, workflow reload, source invalidation and cache replay. The final cached prompt reported all 12 graph nodes cached, succeeded, and returned both pose-node and sampler UI outputs. PNG metadata replay after moved/scaled linked-pose masks produced an identical RGB pixel hash: `7cb98b81543aa8e7d9c412a4f38387b18206d6edb38941dfcabb519fc7ca6d59` (1024×1536). These are local Linux checks, not a claim of Windows runtime verification or stronger pose adherence.

GitHub compatibility CI for implementation commit `fd5260d` passed on Linux with ComfyUI v0.3.76 and current core, and on Windows with current core: [run 39766861816](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions/runs/39766861816). This covers CPU integration and JavaScript controls; real GPU generation and browser interaction were verified locally on Linux.
