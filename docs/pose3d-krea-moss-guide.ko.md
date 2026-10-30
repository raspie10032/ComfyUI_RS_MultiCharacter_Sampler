# Krea 2·MOSS에서 3D 포즈와 캐릭터 영역 함께 쓰기

1.0.10 한글 버전 기준입니다. 3D 편집기에서 자세를 정한 다음, **학습된 포즈 어댑터로 자세를 유도하면서 번호별 프롬프트로 캐릭터를 배치**합니다. 정확한 손·접촉·관절 각도를 보장하는 기능은 아닙니다.

## 1. PNG부터 불러오기

확장을 업데이트하고 ComfyUI를 재시작한 뒤 브라우저도 새로고침하세요. 아래 링크의 **원본 PNG를 저장해 ComfyUI 캔버스에 드래그**하면 노드와 연결이 복원됩니다. 비교용 JPG에는 워크플로가 없습니다.

- [Krea 2 — 진·유라, 팔 들기](../examples/pose3d/genshin-krea2-pose.png)
- [MOSS — 진·유라, 팔 들기](../examples/pose3d/genshin-moss-native-pose.png)

체크포인트·텍스트 인코더·VAE는 본인이 설치한 파일로 선택하세요. 어댑터는 베이스 모델을 대신하지 않습니다. Krea 2·MOSS를 지원하는 ComfyUI 코어가 필요하며, 실제 시험 코어는 `5cc4b87`입니다. 선택지에 해당 모델 계열이 없으면 코어부터 업데이트하세요.

| 항목 | Krea 2 시험본 | MOSS 시험본 |
| --- | --- | --- |
| 모델 | Krea 2 Turbo FP8 scaled | MOSS Image SFT BF16 |
| 텍스트 인코더 | Qwen3-VL 4B FP8 scaled, `krea2` | Qwen3.5 9B INT8 converted-rotary, `moss_image` |
| VAE | Qwen Image VAE | Flux2 VAE |
| 캐릭터 배치 | `regional` | `moss_native` 또는 활성 어댑터와 `auto` |
| 포즈 입력 | 3D 관절에서 만든 OpenPose 지도 | 3D 인물 색상 지도＋깊이 지도 |

## 2. 연결은 두 갈래

```text
모델 MODEL ───────────────┐
VAE ─────────────────────┼→ RS 3D Pose Adapter → MODEL → RS MultiCharacter Sampler
RS 3D Pose Masks         │
  ├ scene_json ──────────┘
  └ building_pipe → Character Prompt → Finalize → character_pipe → 같은 샘플러
```

샘플러에는 CLIP과 같은 VAE도 연결합니다. `scene_json`은 포즈를, `building_pipe`는 번호별 캐릭터 영역을 전달합니다. **MODEL만 연결하면 캐릭터별 프롬프트·영역 연결을 대신하지 못합니다.** 필요하면 LoRA·Position 노드도 Finalize 전에 연결할 수 있습니다. 번호로 합쳐지는 빌딩 노드는 순서와 관계없이 조립되지만, Finalize는 마지막에 둡니다.

포즈 어댑터는 장면 전체를 유도하고, 캐릭터 프롬프트·영역은 각 인물의 외형을 배치합니다. 캐릭터마다 독립적인 포즈 어댑터를 적용하는 구조는 아닙니다.

## 3. 자세와 캐릭터 지정

1. **RS 3D Pose Masks → Open 3D editor**를 누릅니다.
2. 인물 번호 1·2가 Character Prompt의 1·2와 맞는지 확인합니다. 예제는 1번 진, 2번 유라입니다.
3. 관절을 골라 회전하거나 앉기·팔 들기 프리셋을 적용합니다. 인물 전체 이동과 카메라도 조절할 수 있습니다.
4. **Apply to node**로 반영합니다. 편집기와 샘플러의 가로·세로 비율을 맞춥니다.
5. 캐릭터 프롬프트에는 외형·의상, 공통 프롬프트에는 배경·장면을 적고 생성합니다. 앉기에는 의자 같은 지지물도 적으면 좋습니다.

**MOSS 네이티브에서는 인물 마스크가 외곽 사각형으로 변환됩니다.** 색상·깊이 포즈 제어는 별도로 유지되지만, 실루엣 경계와 리저널 경계 강도 설정은 사용하지 않습니다. Krea 2는 실루엣 리저널 경로를 사용합니다.

새 샘플러의 `layout_method=auto`는 활성 MOSS 포즈 어댑터가 있으면 `moss_native`, 그 밖에는 `regional`을 고릅니다. 저장된 명시적 선택은 유지됩니다. MOSS에서 포즈 OFF/ON만 비교할 때는 두 조건 모두 `moss_native`로 고정하세요. OFF에서 `auto`를 쓰면 배치 경로도 바뀔 수 있습니다. 실행 정보에 표시되는 `Layout: auto → moss_native`로 실제 경로를 확인할 수 있습니다.

## 4. 처음 쓸 설정

| 설정 | Krea 2 Turbo | MOSS SFT |
| --- | --- | --- |
| 예제 해상도 | 768×1024 | 768×1024 |
| 스텝 / CFG | 10 / 1 | 50 / 4 |
| 샘플러 / 스케줄러 | Euler ancestral / SGM uniform | Euler ancestral / SGM uniform |
| 포즈 강도 | 1 | 1 |
| 시작 / 종료 비율 | 0 / 1 | 0 / 0.5 |

종료 비율은 전체 디노이징 구간에 대한 값입니다. 위 값은 실제 시험한 출발점이며 모든 모델의 최적값은 아닙니다. MOSS는 포즈 지도를 꺼도 제어 LoRA와 확장 입력 임베더가 샘플링 동안 남습니다. 완전한 OFF 비교는 `strength=0`으로 하세요.

Krea 약 229 MB, MOSS 약 313 MB의 전용 가중치는 **최초 실제 사용 시 자동 다운로드**하며 노드에 진행도가 표시됩니다. 파일은 `models/loras/rs_reference/krea_pose/` 또는 `moss_pose/`에 저장됩니다. 강도 0이나 시작=종료이면 받지 않습니다. 이 제어 LoRA를 일반 LoRA 로더에서 다시 중복 적용하지 마세요. 다운로드 관련 모듈 오류가 나면 ComfyUI Python으로 `requirements-reference.txt`를 설치하세요.

## 5. 실제 비교와 한계

모델 2종 × 자세 6종 × 같은 시드 OFF/ON 및 다른 시드 ON으로 **36장**을 생성했습니다. 행동 지시는 프롬프트에 넣지 않았고, 스타일·캐릭터 LoRA도 쓰지 않았습니다. 포즈용 제어 LoRA는 사용했습니다.

아래 열은 **3D 입력 → 시드 1 OFF → 시드 1 ON → 시드 2 ON**입니다.

![Krea 2 팔 들기·앉기·마주 보기](../examples/pose3d/genshin-diverse/krea-page1.jpg)

![MOSS 팔 들기·앉기·마주 보기](../examples/pose3d/genshin-diverse/moss-page1.jpg)

팔 들기·앉기 같은 큰 자세에는 두 모델 모두 반응했습니다. 손잡기·포옹 접촉점, 정확한 측면·관절 각도는 약합니다. MOSS 측면 앉기에서는 한 시드에 캐릭터와 포즈 역할이 뒤바뀌었습니다. 기존 스타일 LoRA 병용 시험의 추가 인물 문제도 해결됐다고 보장하지 않습니다.

36건 실행 성공은 36건 자세 성공을 의미하지 않습니다. 이번 표본은 두 캐릭터·두 ON 시드이며, 복잡한 상호작용이나 더 많은 인원을 일반화할 수 없습니다. [전체 시험 조건과 관찰 결과](pose3d-genshin-diverse-validation.md)를 참고하세요.

## 6. 함께 연결할 때 주의

- **일반 RS MultiCharacter Sampler**를 사용합니다. 점진 해상도 샘플링·동시 이미지 참조·다른 어텐션 교체와의 혼용은 현재 제한됩니다.
- 새 어댑터는 **Krea 2 Turbo·MOSS용**입니다. Anima 2B는 기존 `pose_image → Apply Anima LLLite → MODEL` 경로를 사용합니다. SDXL·SD1.5·FLUX용 포즈 지원이 추가되는 것은 아닙니다.
- 다른 체크포인트·양자화·캐릭터별 LoRA 조합은 별도 시험이 필요합니다. 출력이 생겨도 인원·캐릭터·자세 배정을 직접 확인하세요.

## 원본 자료

- https://huggingface.co/thedeoxen/Krea-2-pose-controlnet
- https://github.com/ostris/ComfyUI-Krea2-Ostris-Edit
- https://huggingface.co/darask0/MOSS-Image-color-depth-control
- [라이선스와 이식 범위](../THIRD_PARTY_NOTICES.md)

3D 편집기·마스크·번호별 파이프는 RS 기능이고, 자세를 읽는 능력은 각 모델용으로 학습된 가중치를 사용합니다.
