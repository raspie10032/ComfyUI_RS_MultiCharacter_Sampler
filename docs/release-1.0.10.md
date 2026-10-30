# 1.0.10 Hangeul

2026-10-30. Corrected Registry package following 1.0.9.

- Includes the editable character STRING sources and connections in all five
  Krea/MOSS workflow PNGs. Frontend workflows now preserve the same captions
  as their embedded API requests.
- Includes the explicit update-ComfyUI error when an older core cannot provide
  scheduled MOSS pose conditioning. Disabled pose and Krea passthrough remain
  available on their supported paths.
- Aligns the package manifest, runtime `__version__`, five README release links
  and current guide at **1.0.10**. A regression checks version agreement.
- Publishes these corrections under a new Registry version because the already
  submitted 1.0.9 package cannot be overwritten.

Pose routing and image-generation behavior are unchanged from the corrected
GitHub 1.0.9 release. See [1.0.9 feature notes](release-1.0.9.md), the
[36-image audit](pose3d-genshin-diverse-validation.md) and the
[Korean guide](pose3d-krea-moss-guide.ko.md) for setup and known limitations.

**한국어:** Registry와 GitHub의 배포 내용을 맞춘 수정 버전입니다. 워크플로 PNG의
편집 가능한 캐릭터 프롬프트 연결과 구형 코어 오류 안내를 포함합니다.
업데이트 후 ComfyUI를 재시작하고 브라우저를 새로고침하세요.

## Verification

Local Python regression: 405 tests run, no failures, 7 conditional skips.
UI regression: 15 test files passed. The new release regression checks the
runtime version, manifest, all five README links and the release-note file.
This patch changes version metadata and distribution documentation; the existing
pose-image audits remain the generation-quality evidence.
