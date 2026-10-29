# 1.0.7 Hangeul

2026-10-29. This release includes independently selectable experimental tools;
it does not enable all adapters together or replace existing sampling defaults.

## 3D scene and pose guidance

- Add **RS 3D Pose Masks (Experimental)**: a local, offline editor with skinned
  human bodies, joint/hand/finger controls, person transforms and camera controls.
  Apply the scene to create numbered full/visible silhouettes in the existing
  building pipe. The browser and CPU renderer share the same scene/rig data.
- Output a separate shaded `pose_image` for a compatible learned pose adapter.
  Native **Apply Anima LLLite** patches can run alongside RS regional routing.
  Masks need no inference weights; learned pose guidance requires a separately
  installed matching adapter. Actual pose generation is validated on Anima 2B.
- Preserve legacy ellipsoid scenes, numbered assignments, output indices and
  existing building-pipe data. Clip masks at the canvas edge. Pose guidance is
  not exact joint/contact control; frontal multi-person seating remains weak.
- Include a real generated [workflow PNG](../examples/pose3d/anima-native-pose.png),
  [setup instructions](pose3d.md) and [feature-isolation results](pose3d-validation.md).

## Reference alternatives

- Add explicit **Auto: Anima v2 (2B)** selection on the experimental MODEL
  reference adapter. It computes independent reference K/V banks once and reuses
  them during generation; numbered references retain their regional routing.
  Active use downloads pinned weights with hash verification and progress.
- Keep the pilot reference path as the automatic default. Full-duration v2 was
  about 29–34% faster in the measured two-character cases, with higher peak
  allocated memory and visible hair/clothing errors. These are small comparisons,
  not a universal benchmark or a recommendation to replace the pilot.
- Keep references active through the final step by default. Cutting at step 16
  remains a quality tradeoff, not a recommended optimization preset.
- Include the separately selectable experimental **Role K/V** backend and
  model-matched pilot adapters for **Anima 2B / 2.9B**. Each path has different
  restrictions: Role K/V and v2 target 2B; v2 rejects character LoRAs, whereas
  Role K/V requires its documented Normal-mode/balanced-routing setup.
- Pose patches and image-reference adapters cannot be combined in this release.
  No weights are bundled. See [pilot setup](anima-reference-frame.md),
  [Role K/V](anima-role-kv.md), [v2 results](anima-reference-v2.md) and
  [2.9B validation](anima29-reference-validation.md).

## Evidence and update

Legacy compatibility: actual CUDA attention tests passed with PyTorch 2.5.1,
xFormers 0.0.28.post3 and ComfyUI v0.3.76 (FP16/BF16; native and regional
paths). This is kernel/API verification, not a full image-quality benchmark.
Windows now rechecks reference-weight hashes on reuse to avoid timestamp-cache
collisions after a same-size file overwrite. [Scope and reproduction](xformers-validation.md).

The 3D editor integration has 12 paired generation outputs and one complete
UI-submitted workflow execution. A separate 24-image ablation uses three scenes,
two seeds and four conditions: baseline, regional only, pose only, both. Style
LoRAs, image references and action captions were absent in that ablation. Pose
guidance induced raised-arm and oblique seated poses; frontal two-person seating
failed even without RS regions. Exact poses and identity are not guaranteed.
The reference-v2 experiment contains 14 generated images; its speed/memory and
quality findings are documented separately from the pose results.

Restart ComfyUI and refresh the browser after updating. Use the existing sampler
and character workflow normally unless explicitly selecting these new options.
The 3D editor is in this local-model extension; no separate 3D editor is installed
by the NovelAI Request package. Upstream code, asset and model-license references
are retained in [third-party notices](../THIRD_PARTY_NOTICES.md).

**한국어:** 3D 인체 편집으로 번호별 마스크를 만들고, 별도 Anima 2B 포즈
어댑터로 자세를 유도합니다. 마스크만 사용하면 추가 가중치는 필요 없습니다.
두 기능은 독립적으로 쓸 수 있으며, 관절·손 접촉의 정확성은 보장하지 않습니다.
참조 v2는 별도 선택 기능으로 추가했고 기존 참조 기본값은 유지합니다.
