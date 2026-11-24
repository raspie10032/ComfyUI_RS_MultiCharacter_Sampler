# 1.1.14 Hangeul

- **Anima 2B 3D pose.** Choose `outline_7000` or `shaded_6200` in **Anima LLLite model** on **RS 3D Pose Masks**. `outline_7000` is the default. [3D pose guide](pose3d.md)
- **SnapRef v2a on 2B and 2.9B.** Select `snapref` for character and style or `snapref_char` for character cues in each numbered **Image Reference** node. Modes can differ by slot. Use Normal application for character LoRAs. [Image reference guide](image-reference.md)
- **Reference Frame v2 on 2B and 2.9B.** Select `reference_frame_v2` directly on the numbered node. On 2.9B, the 2B weights map to the original 28 blocks. On 2B, both SnapRef and Reference Frame v2 can run alongside the 3D pose LLLite. [Reference Frame v2 guide](anima-reference-v2.md)
- **Role Ref KV v2/v3 on 2B and 2.9B.** Use `role_kv_v2` or `role_kv_v3` consistently across active slots. V3 also accepts a separate `pose_image`. [Role Ref KV guide](anima-role-kv.md)

Install the optional image-reference dependencies from `requirements-reference.txt` with ComfyUI's Python. Active adapter weights are downloaded and verified on first use. Restart ComfyUI and refresh the browser after upgrading. On 2.9B, the 3D editor supplies numbered masks.

## 한국어

- **Anima 2B 3D 포즈**의 **Anima LLLite 모델**에서 `outline_7000`(기본값) 또는 `shaded_6200`을 선택할 수 있습니다. [3D 포즈 가이드](pose3d.md)
- **이미지 참조**의 `snapref`는 캐릭터와 그림체를 함께 반영하고, `snapref_char`는 캐릭터 외형을 중심으로 반영합니다. 슬롯마다 모드를 고를 수 있습니다. `reference_frame_v2`도 같은 노드에서 선택할 수 있습니다. 두 방식 모두 2B·2.9B를 지원하고, 2B에서는 3D 포즈 LLLite와 함께 쓸 수 있습니다. [이미지 참조 가이드](image-reference.md)
- **Role Ref KV v2·v3**는 2B·2.9B를 지원합니다. 활성 슬롯에 같은 버전을 지정하고, v3에서는 `pose_image`에 별도 포즈 이미지를 넣을 수 있습니다. [Role Ref KV 가이드](anima-role-kv.md)
