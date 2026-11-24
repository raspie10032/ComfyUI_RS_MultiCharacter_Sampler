# 1.1.15 Hangeul

- Krea2 and MOSS now explain their available settings when learned 3D pose conflicts with image references. To keep the references and 3D character masks, set `pose_control=masks_only` and use `regional` layout. To keep learned pose guidance, turn off the image references. For workflows with the legacy RS 3D Pose Adapter, set that node's strength to `0` to keep the references.
- RS Workspace updates the generation controls when pose or reference settings change. References with zero strength or disabled slots no longer trigger the conflict.
- For Krea2 and MOSS, choose the default `reference_frame` on each numbered Image Reference node. This setting routes to the corresponding model's image-reference backend.

See the [3D pose guide](pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental).

## 한국어

- Krea 2·MOSS에서 학습형 3D 포즈와 이미지 참조가 충돌하면 해당 모델에 맞는 설정을 안내합니다. 이미지 참조와 3D 캐릭터 마스크를 유지하려면 `pose_control=masks_only`와 `regional` 배치를 사용하세요. 학습형 포즈를 유지하려면 이미지 참조를 끄세요. 이전 RS 3D Pose Adapter를 연결한 워크플로에서는 그 노드의 강도를 `0`으로 설정하면 이미지 참조를 쓸 수 있습니다.
- RS Workspace에서 포즈나 참조 설정을 바꾸면 생성 가능 여부를 즉시 갱신합니다. 강도가 0이거나 꺼진 슬롯의 참조는 충돌 검사에서 제외합니다.
- Krea 2·MOSS의 번호별 Image Reference 노드에서 기본값인 `reference_frame`을 선택하면 각 모델의 이미지 참조 방식이 적용됩니다.
