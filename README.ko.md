# RS MultiCharacter Sampler

ComfyUI에서 캐릭터별 프롬프트·LoRA·영역을 지정해 생성하고, 인물을 감지해 부분 보정하는 확장입니다. 좌표·박스·마스크로 각 캐릭터의 외형을 적용할 위치를 유도합니다.

[English](README.md) · [日本語](README.ja.md) · [문서 모음](docs/README.md) · [변경 기록](CHANGELOG.md) · [릴리스](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md)

**현재 버전: [1.0.3 한글](docs/release-1.0.3.md).** 로컬 모델로 실행하며 RS NovelAI 확장이나 API 키가 필요하지 않습니다.

![LoRA 없이 생성한 Anima 2인 예제](examples/two-characters-result.png)

## 주요 기능

- 공통 장면과 캐릭터별 문장을 분리하고, **캐릭터·글자 합계 최대 10영역**을 설정합니다.
- 캐릭터별 LoRA를 선택하고 좌표·박스·외부 마스크·번호별 마스크 그리기로 배치합니다.
- 컬러 OpenPose PNG·JSON·`POSE_KEYPOINT`에서 편집 가능한 인물 마스크를 만듭니다.
- 원래 캐릭터 프롬프트와 해당 LoRA로 감지된 인물을 부분 보정합니다.
- PNG/WebP에 생성 정보를 저장하고 이미지 로더로 복원합니다.

좌표와 마스크는 프롬프트를 적용할 영역을 유도합니다. 정확한 인원수·정체성·자세·철자는 모델에 따라 달라집니다. [캐릭터 이미지 참조](docs/image-reference.md)도 **실험적으로 지원하지만 권장하지 않습니다.** 맞는 캐릭터 LoRA가 있다면 우선 사용하세요.

## 설치와 업데이트

ComfyUI-Manager에서 **RS MultiCharacter Sampler**를 검색하거나 [Comfy Registry](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)에서 설치하세요. 패키지 ID는 `comfyui-rs-multicharacter-sampler`입니다.

Git 설치는 **`ComfyUI/custom_nodes` 안에서** 실행합니다.

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

Manager로 업데이트하거나 기존 Git 설치 폴더에서 `git pull --ff-only`를 실행하세요. 설치·업데이트 후 **ComfyUI를 재시작하고 브라우저를 새로고침**합니다. 같은 확장을 중복 설치하지 마세요.

Python **3.11 이상**과 Torch·NumPy·Pillow가 필요합니다. ComfyUI 자체가 선택한 모델을 지원해야 하며, 확산 모델·맞는 텍스트 인코더·VAE는 직접 준비합니다. Load CLIP에 `krea2`나 `moss_image`가 없으면 코어와 Python 환경부터 업데이트하세요. [호환성·시험 버전](docs/compatibility.md)

선택 기능은 추가 설치가 필요합니다.

| 기능 | 준비 |
| --- | --- |
| 로컬 디테일러 | Manager에서 **ComfyUI-Impact-Pack**·**ComfyUI-Impact-Subpack**을 설치하고 ComfyUI의 Python으로 `requirements-detailer.txt`를 설치합니다. SAM은 선택 사항입니다. 선택한 감지·태거 카탈로그 모델이 없으면 실행할 때 내려받습니다. |
| 이미지 참조 · 실험적 | ComfyUI의 Python으로 `requirements-reference.txt`를 설치합니다. 활성 참조로 생성할 때 추가 모델을 받을 수 있으며 OFF·강도 0에서는 읽지 않습니다. [방식과 한계](docs/image-reference.md) |

## 예제로 시작하기

[역할별 Anima 2인 워크플로](examples/modular/two-characters-anima.json)를 불러오거나 아래 표에서 모델에 맞는 예제를 고르세요. UI에서는 일반 JSON을 사용하며 `-api.json` 파일은 API용입니다. [워크플로 원본 PNG](examples/two-characters-workflow.png)를 캔버스로 끌어다 놓아도 됩니다.

1. 로더에서 설치된 **MODEL·CLIP·VAE**를 선택합니다. Anima 예제의 Load CLIP 타입은 `stable_diffusion`입니다.
2. STRING 문장 노드를 **RS 캐릭터 프롬프트**의 번호별 입력에 연결하고 각자의 외형·행동을 씁니다. 샘플러의 공통 프롬프트에는 전체 인원·장면·화풍을, 공통 네거티브에는 제외할 내용을 적습니다.
3. **RS 캐릭터 위치**에서 배치합니다. X/Y는 0~1, 왼쪽 위는 `(0, 0)`입니다. 프롬프트·LoRA·위치의 같은 번호가 같은 캐릭터입니다.
4. 조립 노드를 **RS 최종 캐릭터 파이프**로 마무리하고 `character_pipe` 출력을 **RS MultiCharacter Sampler**에 연결합니다. LoRA·위치는 생략할 수 있고 역할 노드의 연결 순서는 자유입니다.
5. **모델 계열 프리셋 → 프리셋 적용**을 누르고 해상도와 모델별 설정을 확인한 뒤 실행합니다. 프리셋은 샘플링·영역 설정을 복사합니다. 모델·LoRA·문장·배치·해상도·시드는 별도로 선택하세요.

자동 저장은 `output/RS_MultiCharacter/`에 PNG·무손실 WebP·손실 WebP로 생성 정보를 기록합니다. 편집용 워크플로까지 이미지에 넣으려면 ComfyUI 기본 **Save Image**를 사용하세요.

[역할별 입력 사용법](docs/modular-characters.md) · [프리셋 설정값](docs/model-presets.md) · [Anima 샘플러·스케줄러 비교](docs/sampler-combinations.md)

## 지원 모델과 예제

아래 값은 예제의 시작 설정입니다. 모델과 장면 전체에 통하는 품질 보장값은 아니며 FLUX는 변형별 워크플로를 사용하세요.

| 모델 계열 | 워크플로 | 시작 설정·범위 |
| --- | --- | --- |
| **Anima** | [2인 예제](examples/modular/two-characters-anima.json) | 기본 예제. 맞는 인코더와 Qwen Image VAE를 연결합니다. 기본 샘플러는 Euler ancestral / SGM uniform입니다. |
| **SDXL / Illustrious** | [2인 예제](examples/two-characters-sdxl.json) · [캐릭터 LoRA](examples/character-lora/illustrious.json) | Load Checkpoint에서 MODEL·CLIP·VAE를 받습니다. 기본 예제는 30스텝·CFG 5.5·Euler ancestral / normal입니다. [시험한 파생 모델과 한계](docs/sdxl-validation.md) |
| **FLUX.1 / 2 / 3** | [모델별 예제](examples/flux) | Dev·Schnell·Klein 변형을 포함합니다. [시험 조합과 검증](docs/flux-validation.md) |
| **Krea 2 Turbo** | [2인 예제](examples/two-characters-krea2.json) · [캐릭터 LoRA](examples/character-lora/krea2.json) | 8스텝·CFG 1·Euler / simple. Qwen3-VL 4B(`krea2`) + Qwen Image VAE. CFG 1에서는 공통 네거티브가 적용되지 않습니다. |
| **MOSS-Image SFT** | [기본](examples/two-characters-moss.json) · [8스텝 LoRA](examples/moss-8step/two-cfg3.json) | 기본은 50스텝·CFG 3·Euler / simple. Qwen3.5 9B(`moss_image`) + Flux2 VAE. [8스텝 설정](docs/moss-8step.md)은 별도 가속 LoRA가 필요합니다. |
| **SD1.5 · 실험적·불안정** | [2인 예제](examples/two-characters-sd15.json) | 실행은 확인했으나 인원수·외형 분리가 불안정합니다. [시험과 한계](docs/sd15-validation.md) |

Krea 2·MOSS의 영역 생성은 실험 지원입니다. MOSS는 일반 ComfyUI CFG를 쓰며 공식 파이프라인의 네거티브 분기 22번 레이어 생략을 적용하지 않습니다. [모델 파일·시험 범위](docs/krea-moss-validation.md)

## 캐릭터 LoRA와 어댑터

**RS 캐릭터 LoRA**에서 번호별 파일·모델 강도·CLIP 강도를 선택합니다. 샘플러 앞의 일반 ComfyUI LoRA 로더는 전체 모델에 적용됩니다. 체크포인트와 어댑터의 모델 구조·차원이 맞아야 합니다.

- **정밀 적용**이 기본입니다. LoRA 설정별 예측을 독립 계산하고 지원되는 경우 작은 행렬 최적화를 사용합니다.
- **일반 적용**은 지원되는 Anima·SDXL 선형 LoRA의 레이어 계산을 공유합니다. 미지원 모델·어댑터는 이유를 표시하고 정밀로 처리합니다. 두 모드는 캐릭터 세부가 달라질 수 있습니다.
- **LoRA·LoCon/Tucker·DoRA·LoHa/DoHa·LoKr/DoKr·GLoRA·OFT/BOFT·IA³·차원이 맞는 diff/set 패치**를 지원합니다. MOSS INT8·FP8의 Q/K/V 부분 적용 LoRA도 처리합니다. 복잡한 형식은 시간과 임시 메모리를 더 쓸 수 있습니다.

**T-LoRA·GLoKr·GGUF/사용자 정의 텐서·레이어 크기를 바꾸는 패치는 이번 어댑터 경로의 지원 범위 밖입니다.** 모델·CLIP 제한과 수치 검증은 [어댑터 형식 안내](docs/adapter-formats.md)를 참고하세요. [LoRA 사용법](docs/regional-lora.md) · [모드 비교](docs/shared-lora-experiment.md) · [캐릭터 LoRA 시험 조합](docs/character-lora-matrix-20261021.md)

## 배치·마스크·부분 보정

**RS 캐릭터 위치**의 번호를 선택해 좌표·박스·마스크를 이동하고 크기를 조절합니다. 외부 MASK는 **RS 캐릭터 마스크**, 밑그림 위에 직접 칠하려면 **RS 캐릭터 마스크 그리기**를 사용하세요. 밑그림 이미지는 표시용입니다. [마스크 사용법·예제](docs/character-masks.md)

**캐릭터 2명 + 단어 1개**는 슬롯 3개를 사용합니다. 두 명은 `character`·포인트, 글자는 `text`·박스로 설정하고 해당 STRING에 실제 단어를 연결합니다. 글자 행의 LoRA는 None으로 둡니다. 물체는 `character`·박스에 물체 설명을 씁니다. `layout_method=regional`을 사용하며 MOSS 공식 배치 모드는 모든 영역에 박스가 필요합니다. [혼합 예제](examples/epsilon) · [물체 예제](examples/epsilon/objects) · [배치 안내](docs/regional-layout.md)

**RS OpenPose 마스크(실험적)**는 대략적인 인물 영역을 만듭니다. 뼈대 자체를 모델에 넣지는 않습니다. 부위 이름 유도는 기본 OFF이며 Anima·SDXL에서 지원합니다. **RS 캐릭터 상호작용**의 추가 분리 유지는 Anima·SDXL·실험적 SD1.5에서 겹치지 않는 영역에 적용됩니다. 정확한 관절·접촉은 보장하지 않습니다. [입력·미리보기·한계](docs/openpose-mask-guides.md) · [포즈 예제](examples/openpose)

부분 보정은 [생성 + 디테일러 예제](examples/two-characters-detailer-anima.json)로 시작하세요. 이미지·캐릭터 파이프·동일한 MODEL/CLIP/VAE를 **RS MultiCharacter Detailer**에 연결하고 **RS Detection Combine Loader**·**RS Character Tagger Loader**를 추가합니다. 얼굴 SEGM·WD ViT v3·디노이즈 **0.25**부터 시작하세요. 태거는 원래 캐릭터 문장을 선택하며 추론한 태그를 보정 문장에 덧붙이지 않습니다. 결과의 캐릭터 매칭 보고서를 확인하세요. [실행 검증과 한계](docs/detailer-validation.md)

## 이미지에서 생성 정보 복원

원본 PNG/WebP를 **RS MultiCharacter Load Image**에서 열고 캐릭터 파이프를 샘플러에 연결합니다. 이미지의 문장·캐릭터 설정이 공통 문장 입력을 대체합니다. **use_image_settings**를 켜면 시드·해상도·샘플링·영역 설정도 복원합니다. 프리셋이나 현재 노드 설정을 쓰려면 끄세요.

모델·LoRA·CLIP·VAE는 직접 연결해야 하며 메타데이터로 자동 설치·로딩하지 않습니다. 이미지 참조는 원본 이미지를 다시 연결해야 합니다. 문장과 시드로 다시 생성하는 기능이며 마스크 img2img는 디테일러에서 별도로 수행합니다. NAI V4 캐릭터 캡션을 가져올 수 있지만 NAI 샘플링 설정을 로컬에 그대로 재현하지는 않습니다. [메타데이터·복원 범위](docs/architecture.md)

## 노드 구성

현재 **15개 노드**를 등록합니다. 노드 이름·선택 안내·도움말은 ComfyUI의 한국어·일본어·영어·중국어 간체·번체 설정을 따릅니다.

| 노드 | 용도 |
| --- | --- |
| 캐릭터 프롬프트 / LoRA / 위치 / 최종 캐릭터 파이프 | 번호별 캐릭터 설정을 조립해 샘플러·디테일러에 전달합니다. |
| 캐릭터 마스크 / 마스크 그리기 | 외부 마스크를 연결하거나 번호별 영역을 칠합니다. |
| OpenPose 마스크(실험적) / 캐릭터 상호작용 | 포즈에서 영역을 만들고 겹침 주변의 분리를 조절합니다. |
| 이미지 참조(실험적·비권장) | 캐릭터 번호에 참조 이미지를 연결합니다. |
| MultiCharacter Sampler / Load Image | 생성하고 저장된 설정을 복원합니다. |
| MultiCharacter Detailer / Detection Combine Loader / Character Tagger Loader | 인물을 감지·매칭하고 부분 보정합니다. |
| MultiCharacter Prompts · 구형 | 기존 워크플로 호환용 통합 입력입니다. 새 워크플로에는 역할별 노드를 사용하세요. |

## 한계와 문제 해결

- 실행당 이미지 1장, 입력은 최대 10슬롯입니다. 밀집 배치·교차하는 소품은 인물 중복·누락·외형 혼합·칸 분리를 만들 수 있습니다. 캐릭터가 하나면 전체 화면을 사용하므로 좌표만 옮겨도 인물이 이동하지는 않습니다.
- 영역 샘플러는 공통 네거티브를 사용합니다. 캐릭터별 네거티브와 시간별 텍스트 컨디셔닝은 지원하지 않습니다.
- 영역 샘플러에서 SD2·인페인트/Refiner 체크포인트·FLUX Fill/Control·외부 ControlNet/attention 패치는 지원하지 않습니다. 선택 기능인 이미지 참조는 별도의 방식과 제한을 따릅니다.
- 샘플러는 **2~100스텝·CFG 1~20**을 받습니다. 프리셋은 모델을 자동 판별하거나 품질을 보장하지 않습니다. 모델별 예제부터 시작하세요.
- 복원에는 원본 메타데이터와 같은 모델·실행 환경이 필요합니다. SNS 등은 메타데이터를 지울 수 있고 자동 저장은 관련 없는 EXIF·GPS·카메라 정보를 유지하지 않습니다.
- 오류 제보에는 확장·코어 버전, 정확한 체크포인트·LoRA 버전, 워크플로 JSON과 전체 오류 로그를 [이슈](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/issues)에 첨부하세요.

[문서·검증 색인](docs/README.md)에서 실제 생성 시험, 어댑터 수치 검증, CPU·CI 호환성 검사를 나누어 확인할 수 있습니다.

## 개발과 라이선스

Torch·NumPy·Pillow가 설치된 환경에서 저장소 루트 기준으로 실행합니다.

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

네이티브 통합 검사는 `RS_MC_TEST_COMFYUI`에 ComfyUI 경로를 지정합니다. 전체 JavaScript UI 검사 11종과 코어·OS 조합은 [CI 설정](.github/workflows/tests.yml)에 있습니다.

GPL-3.0-only. [COPYING](COPYING) · [서드파티 고지](THIRD_PARTY_NOTICES.md) · [소스 계보](docs/source-lineage.json)
