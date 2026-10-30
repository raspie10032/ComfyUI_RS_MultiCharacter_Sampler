# 1.0.9 release checks

2026-10-30 (Asia/Seoul). Scope: Krea 2 / MOSS trained 3D pose support,
automatic MOSS layout selection, package version, guides and importable PNGs.

## Local regression checks

```bash
RS_MC_TEST_COMFYUI=/home/raspie/AI/ComfyUI \
RS_MC_TEST_GGUF=/home/raspie/AI/ComfyUI/custom_nodes/ComfyUI-GGUF \
PYTHONPATH=/home/raspie/AI/ComfyUI \
/home/raspie/AI/ComfyUI/.venv/bin/python -m unittest discover -s tests -q

PATH=/home/raspie/AI/ComfyUI/.venv/bin:$PATH \
CAMERA_PYTHON=/home/raspie/AI/ComfyUI/.venv/bin/python \
node --test tests/*_ui.cjs
```

- Python: **402 run, no failures, 7 conditional skips**, 42.235 seconds.
- JavaScript: **15 test files passed**, no failures or skips.
- Package TOML and all five README version labels: **1.0.9**.
- Guide relative-file links and `git diff --check`: passed.

These are source/integration checks, not image-quality evidence. GitHub's
[compatibility workflow](../.github/workflows/tests.yml) independently tests
Linux and Windows CPU environments; use the actual
[workflow run statuses](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions)
for CI and Registry publication status.

## Installed runtime

The candidate's managed files were copied into the existing installation at
`/home/raspie/AI/ComfyUI/custom_nodes/comfyui-rs-multicharacter-sampler`.
The running and pending queues were both empty before restarting only
`comfyui.service`. The resident server registered `RS3DPoseAdapter` after restart.
Both new Genshin PNGs' embedded API requests were submitted to this resident
server and produced successful image outputs:

| PNG | Prompt ID | Actual layout |
| --- | --- | --- |
| `genshin-krea2-pose.png` | `40db8cbe-dcef-4009-a7e4-b29cc7021cce` | `regional → regional` |
| `genshin-moss-native-pose.png` | `280a0bec-c3e5-4922-bbdd-40fb42aea47a` | `auto → moss_native` |

Only the SaveImage filename prefix changed for this repeat. MOSS reproduced
the packaged example's RGB pixels exactly. Krea's mean absolute RGB difference
was 0.602/255; it was not pixel-identical, so exact Krea reproducibility is not
claimed. These two executions verify installed execution, not a new pose-quality
success rate. See the separate
[36-image visual audit](pose3d-genshin-diverse-validation.md) for image quality,
matched OFF/ON design and known failures.

## Workflow PNGs and local artifacts

Each new PNG contains **11 nodes / 12 links**, a 3D scene, frontend `workflow`
metadata and backend `prompt` metadata. Both metadata objects were reread and
checked after saving; the image pixels match their source generated examples.
Both new PNGs were imported in the resident frontend, where both character
STRING fields were visibly restored. MOSS was exported through the frontend
API export; scene, character strings, pose settings and explicit sampler inputs
matched the packaged request. Extra sampler defaults are populated by the UI.

Local evidence, intentionally outside the package:

- `/var/home/raspie/AI/rs-pose-integration-20261030/release-1.0.9-smoke/`:
  exact submitted requests, history receipts and pixel-comparison results.
- `/var/home/raspie/AI/rs-pose-integration-20261030/release-1.0.9-backup/`:
  pre-update files and managed-file manifest.
- `/var/home/raspie/Documents/Codex/RS_MC_1_0_9_Pose_guide_20261030/`:
  Korean illustrated HTML guide, copyable post text and two-workflow PNG ZIP.

No pose-adapter model weights or base checkpoints are bundled. Automatic
first-use downloads are separately tested by the adapter's source tests and
existing live setup evidence; this release smoke used already downloaded weights.

## Editable character-caption correction

The final example audit found literal character captions only in backend metadata,
without STRING sources in the frontend graph. All five Krea/MOSS pose PNGs now
include two connected `PrimitiveStringMultiline` nodes. The added regression
checks every source value, link endpoint and matching backend input, including
Jean/Eula identity in the new examples. This correction does not alter generated
image pixels or the effective character text. The 402-test baseline above
precedes this additional example regression.

## Older core CI correction

The first CI run passed Windows and two newer Linux cores but found an absent
scheduled-conditioning helper on ComfyUI v0.3.76. MOSS itself is unsupported
on that old core. The adapter now gives an explicit update-ComfyUI error for
that request, while disabled pose and Krea conditioning passthrough keep working.
A missing-helper regression exercises this behavior without hiding the failure.
