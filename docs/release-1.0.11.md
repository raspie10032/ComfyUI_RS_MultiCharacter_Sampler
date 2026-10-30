# 1.0.11 Hangeul

2026-10-30 (Asia/Seoul).

- **Image → editable 3D:** drop/select a single-person PNG, JPEG or WebP on
  the 3D pose node. It queues SAM 3D Body estimation locally, saves the estimated
  scene and opens the editor automatically. No extra image/estimator wiring is
  needed. The existing node and output socket order are preserved.
- **Source framing:** retain image aspect ratio, camera and crop. Only the body
  inside the source frame enters silhouettes, pose maps and editable geometry;
  off-frame inferred legs are excluded. Hidden joints/depth within the frame
  remain estimates, so use this as a composition guide.
- **Import while editing:** a one-person scene adopts source framing. In a group,
  replace only the selected person, preserving the other people and scene camera.
  Import applies automatically; later mouse edits use **Apply to node**. Stale
  inference results cannot overwrite a scene changed while estimation was running.
- **Local pose library:** choose a catalogue pose, randomize the selected person,
  or randomize each person independently. Existing placement and prompt IDs stay
  fixed. Samples remain local; no downloaded pose data is included in GitHub or
  Registry packages. Randomization happens when clicked, not during sampling.
- **Requirements and notices:** image estimation needs a ComfyUI core providing
  `SAM3DBody_Loader` / `SAM3DBody_Predict`. First use downloads the pinned 2.83 GB
  model. The separate SAM License is included with the third-party notices.
  Manual 3D posing and masks do not need this inference model.

## Usage

Restart ComfyUI after updating and hard-refresh its browser tab. Add **RS 3D Pose
Masks (Experimental)**, select/drop an image on **Image → 3D**, then click a joint
and drag its rotation rings. **Move person** changes placement; dragging empty
space orbits the camera. Finish with **Apply to node**. Existing pose-adapter
MODEL and `building_pipe` connections still carry different signals and both are
needed for trained pose guidance. See the [full guide](pose3d.md).

**한국어:** 이미지 한 장을 넣으면 자동 추정 후 마우스로 수정할 수 있는 3D 편집기를
엽니다. 반신은 보이는 화면 범위를 유지하고 화면 밖 하체를 출력하지 않습니다.
여러 명을 편집할 때는 선택 인물만 교체합니다. 로컬 포즈 목록의 랜덤 선택도
추가했습니다. 샘플 파일은 로컬에만 보관하며 패키지에는 포함하지 않습니다.

## Verification scope

Release checks and installed-runtime results are recorded in
[1.0.11 validation](pose3d-1.0.11-release-validation.md). These import/editor checks
do not establish exact reconstruction, reliable hands/contact, or new generation
quality. The earlier [Krea/MOSS audit](pose3d-genshin-diverse-validation.md) remains
the separate image-generation evidence.
