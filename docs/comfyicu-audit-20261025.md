# comfy.icu 노드 페이지 대조 — 2026-10-25

대상은 `ComfyUI_RS_MultiCharacter_Sampler`의 등록 노드 15개다. 원격 `main`의
`f02cea2`를 기준으로 각 페이지의 설명, 입력·출력 표, 주의사항을 코드·시험과
대조했다. 사이트의 편집 설명을 사용자 버그 제보로 간주하지 않는다.
페이지의 일부 문장은 최신 입력 표나 현행 코드와도 서로 다르다.

## 수정한 문제

### 1. Mask Drawing 뒤에 이전 OpenPose 부위 정보가 남음

OpenPose로 부위 유도를 켠 파이프를 만든 뒤 Mask Drawing으로 실루엣을 바꾸면
기존 `body_parts`와 `body_part_strength`가 남았다. 새 그림 아래에 이전 포즈의
부위 이름 유도가 적용될 수 있었다. 외부 MASK 노드는 이미 이 정보를 지웠지만
Mask Drawing 경로는 빠져 있었다.

이제 그리기 테이블을 적용할 때 부위 마스크와 강도도 함께 초기화한다. 빈 행으로
되돌린 번호에도 적용하며 원래 파이프는 수정하지 않는다. LoRA·프롬프트·위치
설정의 합성 규칙은 기존과 같다. `test_mask_drawing.py`의 새 회귀 시험이 수정 전
실패했고 수정 후 통과했다.

### 2. Detailer 출력과 저장에서 부위·상호작용 설정 유실

Finalize에서 바로 전달한 파이프에는 원본 생성 스냅샷이 없을 수 있다. 이때
Detailer 저장은 캐릭터 마스크만 기록하고 부위 마스크·강도·상호작용 설정을
놓쳤다. 스냅샷이 있어도 현재 파이프와 다르면 오래된 값을 사용할 수 있었다.
또한 반환 파이프를 새로 만들 때 `interaction_json`을 전달하지 않았다.

이제 현재 파이프의 부위 마스크·강도·상호작용을 저장하고 반환한다. 현재 값이
없으면 이전 스냅샷에 남은 값도 제거한다. 원본 생성 설정과 디테일러 이력은
계속 보존한다. 새 시험은 직접 입력과 오래된 스냅샷, 출력 파이프, PNG·무손실
WebP·손실 WebP의 저장→읽기→파이프 복원을 검사한다. 이 시험도 수정 전 실패했다.

### 3. Interaction 고정 프리셋에서 무효인 숫자 입력이 계속 보임

`baseline`·`delay3`·`delay6`는 `delay_steps`·`decrement` 위젯을 사용하지 않는다.
페이지도 이 혼동을 지적한다. 이제 숫자 입력은 `custom`에서 펼쳐지고, 고정
프리셋에서는 접힌다. 기존 값·저장 순서·연결 소켓은 유지한다. 연결된 프리셋은
실행 시 결정되므로 입력을 보여준다.

선택 항목 설명 패널도 추가했다. 기본은 추가 분리 없음, delay3/6은 비겹침 영역을
3/6스텝 더 보호하고 감소폭은 샘플러 설정을 사용함, custom은 아래 숫자를 사용함을
설명한다. 영어·한국어·일본어·간체·번체를 지원한다.

## 15개 페이지별 확인

| 페이지 | 대조 결과와 조치 |
| --- | --- |
| [Sampler](https://comfy.icu/node/RSMultiCharacterSampler) | 설명의 FLUX 미지원은 오래된 내용이다. 현행 코드에는 FLUX 계열별 경로와 시험이 있다. MOSS native에서 마스크가 사각형이 되는 것은 명시한 동작이며, 자동 저장은 워크플로 저장과 다르다. 이 설명에 맞춰 지원 기능을 축소하지 않는다. |
| [Character Prompt](https://comfy.icu/node/RSMultiCharacterPrompt) | 연결 STRING, 행 수·사용 여부·번호 유지, 캐릭터/텍스트 분기를 확인했다. 인원 수가 포즈나 실제 생성 인원 보장은 아니다. 이번 재현에서 새 수정 항목 없음. |
| [Character LoRA](https://comfy.icu/node/RSMultiCharacterLoRA) | 일반/정밀 선택과 폴백, 텍스트 슬롯 제한을 확인했다. 문장의 모든 LoRA를 같은 범위로 지원한다는 인상은 주의해야 한다. 형식·양자화 제한은 기존 문서와 시험을 따른다. |
| [Character Position](https://comfy.icu/node/RSMultiCharacterPosition) | 점/상자/마스크 이동·크기·클리핑·번호 보존, 입력 소스 우선순위를 확인했다. 1인 점 배치로 인물이 이동하지 않는 것은 전 캔버스 소유 규칙의 결과다. |
| [Character Mask](https://comfy.icu/node/RSMultiCharacterMask) | 흰색 지원 영역, 단일 마스크, 기본 Load Image의 알파 MASK 함정, 좌표·상자 대비 우선순위, 포즈 부위 정보 초기화를 확인했다. 캔버스 밖 마스크만 자르는 기존 동작을 유지한다. |
| [Mask Drawing](https://comfy.icu/node/RSMultiCharacterMaskDraw) | 표시용 배경은 생성 이미지 입력이 아니다. 빈 행은 점/상자로 복귀한다. 포즈 부위 정보가 남는 결함을 수정했다. |
| [Finalize](https://comfy.icu/node/RSMultiCharacterFinalize) | 번호별 합성, 미입력 STRING 오류, 텍스트 상자와 LoRA 제한, 마스크 변환과 부위 중심 이동을 확인했다. 이번 재현에서 새 수정 항목 없음. |
| [Legacy Prompts](https://comfy.icu/node/RSMultiCharacterPrompts) | 신규 조립 노드로의 대체 안내와 기존 워크플로용 등록을 확인했다. 기존 데이터 호환 경로를 유지한다. |
| [OpenPose Masks](https://comfy.icu/node/RSMultiCharacterPoseMasks) | PNG·IMAGE·JSON·POSE_KEYPOINT 우선순위, PNG 좌우 번호와 JSON 원래 번호 차이, 신뢰도·누락 관절, 부위 유도 기본 OFF를 확인했다. 뼈대를 직접 전달하는 ControlNet 기능으로 확대 해석하지 않는다. 후속 드로잉·디테일러 문제는 위에서 수정했다. |
| [Interaction](https://comfy.icu/node/RSMultiCharacterInteraction) | custom 전용 숫자를 다른 프리셋에서 바꿔도 적용되지 않는 혼동을 UI와 설명 패널로 수정했다. 추가 분리는 Anima/SDXL/SD1.5 경로이며 겹침·배경 일정은 바꾸지 않는다. |
| [Image Reference](https://comfy.icu/node/RSMultiCharacterReference) | 실험적·비추천 표시, 해상도·모델별 백엔드 차이, 비활성일 때 다운로드 생략, MOSS native 거부를 확인했다. 이번 시험을 이미지 참조 품질 개선의 증거로 쓰지 않는다. |
| [Load Image](https://comfy.icu/node/RSMultiCharacterLoadImage) | 메타데이터 없는 파일 오류, 프롬프트 복원과 생성 설정 복원 옵션의 차이, 모델 자동 로딩 없음, EXIF 방향 검증을 확인했다. 디테일러 이미지의 부위·상호작용 복원을 보강했다. |
| [Detailer](https://comfy.icu/node/RSMultiCharacterDetailer) | 모호한 매칭 건너뛰기, 1인 태거 생략, 검출 수와 입력 슬롯 수의 차이, 동결 원본 크롭·수정 영역 외 픽셀 보존을 확인했다. 출력 파이프·저장 설정 유실을 수정했다. |
| [Detection Combine Loader](https://comfy.icu/node/RSMultiCharacterDetectionLoader) | SEGM 우선이며 BBOX/SAM을 실제로 건너뛰는 규칙, OFF·자동 다운로드·폴더 목록을 확인했다. 세 모델을 동시에 실행하도록 바꾸지 않는다. |
| [Character Tagger Loader](https://comfy.icu/node/RSMultiCharacterTaggerLoader) | 사전 의존성 검사·선택 모델만 준비·바이트 진행도·태그의 매칭 전용 사용을 확인했다. 페이지의 일반 HF 캐시 안내와 달리 현재 코드는 `models/rs_wd_tagger`를 캐시 루트로 전달한다. 배치 크기는 인식 가능한 캐릭터 수가 아니다. |

## 검증 범위

ComfyUI의 Python 환경에서 다음을 실행했다. CPU 통합은 설치된 ComfyUI와 GGUF
코드를 사용하며, 작은 임의 가중치 모델·합성 CLIP/VAE를 이용한다. 실제 체크포인트
이미지 생성이나 생성 품질 검증과 구분한다.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
RS_MC_TEST_COMFYUI=/path/to/ComfyUI \
RS_MC_TEST_GGUF=/path/to/ComfyUI/custom_nodes/ComfyUI-GGUF \
/path/to/ComfyUI/.venv/bin/python -m unittest discover -s tests -v
node tests/test_interaction_ui.cjs
node tests/test_node_help_ui.cjs
git diff --check
```

- Python: 238개 실행, 237개 통과, 1개 조건부 생략. 설치된 코어는 native bypass를
  지원하므로 이를 지원하지 않는 코어 전용 시험 1개가 생략됐다.
- JavaScript: CI에 등록된 12개 UI 시험 묶음 모두 통과. Interaction의 값·저장 순서,
  콜백, 연결 프리셋, 변환된 소켓, 확장 로딩 순서 양쪽과 5개 언어 패널을 검사한다.
- 실제 PNG·두 WebP 형식으로 파일 저장·재로드·파이프 복원을 검사했다.
- UI 검증은 Node VM의 모의 ComfyUI 노드로 실행했다. 브라우저 화면 조작이나
  상주 ComfyUI에서의 새 이미지 생성 결과를 주장하지 않는다.

별도 작업 공간에서 수정했다. 기존 작업 공간의 미커밋 변경과 설치본은 건드리지
않았으며, 이 대조 작업만으로 새 버전 게시나 외부 페이지 수정은 하지 않는다.
