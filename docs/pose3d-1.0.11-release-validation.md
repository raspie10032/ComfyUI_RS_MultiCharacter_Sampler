# 1.0.11 release checks

2026-10-30 (Asia/Seoul). Scope: image-drop 3D estimation, source-frame clipping,
local pose catalogue/random selection, package version and installed runtime.

## Source and integration checks

```bash
RS_MC_TEST_COMFYUI=/home/raspie/AI/ComfyUI \
RS_MC_TEST_GGUF=/home/raspie/AI/ComfyUI/custom_nodes/ComfyUI-GGUF \
PYTHONPATH=/home/raspie/AI/ComfyUI \
/home/raspie/AI/ComfyUI/.venv/bin/python -m unittest discover -s tests -v

PATH=/home/raspie/AI/ComfyUI/.venv/bin:$PATH \
CAMERA_PYTHON=/home/raspie/AI/ComfyUI/.venv/bin/python \
node --test tests/*_ui.cjs tests/test_pose_image_scene.mjs

# From tools/pose3d:
npm run build
```

- Python: **410 run, 7 conditional skips, no failures/errors**, 42.201 seconds.
- JavaScript: **17 test files passed**, no failures or skips.
- The five source-frame tests check browser/Python clipped-geometry parity,
  crop persistence through serialization, side-view exclusion of off-frame legs,
  group isolation and invalid/empty frame handling.
- Import UI tests cover auto-opening, standalone framing, group replacement,
  duplicate/stale/linked inputs, inference errors, node removal and progress
  listener cleanup. File/drop handlers are exercised with test doubles; this
  does not prove a native file dialog or physical drag gesture.
- Runtime node registration count updated from 21 to 22, including
  `RSImageToPose3D`. Runtime, manifest and all five README release links match
  **1.0.11**. Offline editor bundle rebuilt.

## Installed resident check

Managed source files were copied into the existing
`/home/raspie/AI/ComfyUI/custom_nodes/comfyui-rs-multicharacter-sampler`
installation, retaining a backup of changed files. Model directories, local pose
samples and user workflows were preserved. Both queue lists were empty before
restarting only `comfyui.service` on port 8188.

- New estimator and existing 3D pose nodes registered after restart.
- The local catalogue endpoint returned **1,199 poses**, with no warnings.
- Actual SAM 3D Body inference on the existing Jean bust crop succeeded:
  prompt `c321cc91-c3ef-4460-8c44-03367712c9ce`.
- Result: one editable person, **380×280** source framing and persisted crop
  planes. The resident preview endpoint returned one projected mask.
- Queue submission through inference and preview verification: **3.789 seconds**
  with weights already installed. This includes polling and preview rendering;
  it is not model-only latency or first-download time.

Earlier local browser checks exercised image selection, estimation success and
automatic WebGL editor opening for Jean full/bust crops (three successful runs,
0.855–2.614 seconds with installed weights). That earlier UI evidence is distinct
from the fresh resident API check above. The release-tab check confirmed the
Image → 3D panel appears after restart; it did not repeat native mouse dragging.

The 1,265 original downloaded positional samples and their 1,199 converted
entries remain in `/home/raspie/AI/pose-library`. They are not tracked, packaged
or attached as release assets. Manual posing remains available without them.

## Limits and CI

These are estimation/editor/output checks. They do not establish exact pose
reconstruction or better generated hands/contact. The earlier
[Krea/MOSS generation audit](pose3d-genshin-diverse-validation.md) remains
separate evidence. Single-image estimation needs the newer SAM3D core nodes;
an older ComfyUI should still load the extension and explain the missing
dependency when image estimation is requested.

The compatibility workflow checks Linux/Windows CPU environments and now runs
both image-import UI regressions. Inspect the runs for the release commit in
[GitHub Actions](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions)
for the independent CI and Registry publication outcomes.
