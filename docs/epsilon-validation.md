# 0.1.5 Epsilon candidate validation

Development branch: `codex/0.1.5-epsilon-bbox`. Base: `66a32eae01eadb4865359c13c964b06993ef81ed` (0.1.4 Delta). Public main and the production installation were not replaced in this task.

## Implemented behavior

- Optional character rectangles, overlapping captions and uncovered common-prompt background.
- `points`, `boxes`, `mixed` layouts. In mixed mode explicit boxes override point regions at every attention resolution; text always uses a box.
- 1–10 total active regions. Character slots and literal text regions are distinct; text never enters face matching or NAI character captions.
- Separate MOSS native structured JSON generation. Requires boxes everywhere; region schedules are intentionally not applied in native mode.
- Normalized center/size UI, preview, Korean/Japanese labels, compatibility with old widget positions.
- PNG/WebP metadata round trips preserve geometry and text; the image loader reconstructs the pipe. Ordinary autosave still has no ComfyUI workflow.

## Evidence

27 completed runtime history records and corresponding output images were retained in the local validation bundle. These comprise 18 initial point/box/swap/resize/overlap cases, 6 two-people-plus-HELLO cases, and 3 final-code/restore/browser replays. All cases are local model generation, with no NovelAI API use.

- Anima: old points regression; four box layouts; all-boxes and mixed 2 people + HELLO; final mixed replay, image-loader replay, browser Run.
- SDXL, SD1.5, Krea2: one overlapping-box execution smoke each. This proves the routes ran, not general geometry, spelling or image-quality reliability.
- MOSS 8-step LoRA: regional left/right and overlap; four native layouts; regional all-boxes, regional mixed and native two people + HELLO.
- MOSS base 50-step: four native layouts and native two people + HELLO.

Current ComfyUI: 95 Python tests passed. ComfyUI v0.3.76: 88 passed and 7 unavailable-model tests skipped. JavaScript slot/UI checks passed. The exported Anima workflow uses the same widget values as the browser-tested workflow. Attention tests cover overlap membership, common-only background at zero common weight, box priority over points at coarse grids, no silent dropped region, and MOSS unweighted literal JSON tokenization. PNG, lossless WebP and lossy WebP metadata tests include text-only and mixed pipes.

The old points sample matches the pre-Epsilon reference pixel for pixel. The final mixed replay matches the prior mixed sample pixel for pixel. Restoring the final PNG through the real loader with deliberately incorrect sampler widget settings produces identical pixels. Browser Run on the imported normal workflow also produces identical pixels. These pixel comparisons used decoded RGB arrays, not PNG file-byte equality.

## Visual findings and limits

Anima followed the left/right box swap. Boxes influence prompt lookup, not exact object outlines. The mixed Anima sample drew two people and HELLO, but clipped the word at the top, used a white background instead of the requested campus, and did not keep whole bodies inside the view.

MOSS 8-step LoRA regional mixed drew two people and correctly spelled HELLO above them while retaining the campus. The text extends beyond the requested rectangle, so exact typesetting is not achieved. Native MOSS base and 8-step LoRA were tested separately. Samples use one seed per layout; no success-rate or universal superiority claim is supported.

This task does not revalidate live detailing with text regions. Source/unit evidence checks exclusion from matching and preservation of boxes/text through detailer metadata. SDXL/SD1.5/Krea2 literal-text quality and mixed-mode image quality were not separately generated; only their overlapping-box routes and CPU mixed membership were checked.

## Reproduce

Load `examples/epsilon/anima-mixed.json` or `moss-mixed.json` in ComfyUI with the candidate installed. Choose available model files, retain the recorded fixed seed and sampler settings, then Run. `moss-native.json` uses boxes for all three regions. The matching `*-api.json` files have no validation-only nodes. All 27 submitted API graphs and history receipts are retained locally.

For tests, from the extension repository:

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI /path/to/python -m unittest discover -s tests
node tests/test_ui.cjs
node tests/test_boxes_ui.cjs
node tests/test_detailer_ui.cjs
```

The isolated test runtime used port 8199. Production port 8188 was kept separate.  Model downloads, installation and ordinary production workflows were not modified by the Epsilon candidate.
