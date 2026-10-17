# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0-alpha1 · Anima · SDXL · Krea 2 · MOSS 실험 알파**입니다. 공통 프롬프트와 캐릭터별 프롬프트·XY를 전용 파이프로 전달하고, 로컬 모델 내부에서 영역별 attention을 조절합니다. RS NAI 확장이나 API 키는 필요 없습니다.

## 설치와 사용

ComfyUI-Manager에서 **RS MultiCharacter Sampler (Anima Alpha)**를 검색해 설치하거나 [Comfy Registry 페이지](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)를 이용하세요. 패키지 ID는 `comfyui-rs-multicharacter-sampler`입니다. 설치 후 ComfyUI를 재시작하세요. 새 항목이 아직 보이지 않으면 Manager 목록을 갱신하거나 Git으로 설치할 수 있습니다.

Git 설치는 이 저장소를 `ComfyUI/custom_nodes` 안에 복제하면 됩니다. 기존 Git 설치본이 있다면 중복 설치하지 말고 그 설치본을 업데이트하세요. 확산 모델·텍스트 인코더·VAE는 직접 준비합니다. 디테일러의 감지·태거 로더는 선택한 카탈로그 모델이 없을 때 실행 중 내려받으며 진행도를 표시합니다.

[워크플로가 포함된 원본 PNG](examples/two-characters-workflow.png)를 캔버스로 끌어다 놓거나 [2인 예제 JSON](examples/two-characters-anima.json)을 불러온 뒤 설치된 Anima 모델·텍스트 인코더·VAE를 선택하세요. 예제의 `Load CLIP` 타입은 `stable_diffusion`입니다. 일반 LoRA 로더를 모델과 샘플러 사이에 연결할 수 있습니다.

1. **RS MultiCharacter Prompts**에서 캐릭터 수와 각 문장을 작성합니다. 기본은 5칸, 최대 10칸입니다. 인원수를 줄이면 숨겨진 슬롯의 이전 문장은 생성에 들어가지 않습니다.
2. X/Y는 0~1이며 왼쪽 위가 `(0,0)`입니다. 같은 좌표의 슬롯은 번호순으로 좌우에 배치합니다.
3. **RS MultiCharacter Sampler**의 공통 문장에는 전체 인원·화풍·장면을, 캐릭터 칸에는 각자의 외형·행동을 씁니다. 시험에서는 캐릭터마다 `1girl` 또는 `1boy`를 썼습니다.
4. 우선 30스텝·CFG 4·Euler ancestral·SGM uniform 기본값으로 실행하세요. 시드의 실행 후 동작은 랜덤으로 바꿀 수 있습니다.
5. 자동 저장은 `output/RS_MultiCharacter`에 PNG 또는 WebP로 생성 정보와 함께 저장합니다. 워크플로는 넣지 않습니다. 워크플로도 필요하면 ComfyUI 기본 이미지 저장 노드를 쓰세요.

공유용 예제 PNG에는 ComfyUI `workflow`·`prompt` 메타데이터가 들어 있습니다. 샘플러의 일반 자동 저장에는 기존처럼 생성 정보만 들어갑니다.

## SDXL 실험 지원

[SDXL 2인 예제](examples/two-characters-sdxl.json)는 일반 체크포인트 로더 하나에서 MODEL·CLIP·VAE를 받습니다. Illustrious XL v1.0과 NoobAI XL epsilon-pred 1.1에서 실제 생성과 좌우 문장 교환을 시험했습니다. SDXL 전체 계열이나 모든 샘플러 조합을 검증한 것은 아닙니다.

예제 시작값은 **30스텝·CFG 5.5·Euler ancestral + normal**, 초기 공통 강도 **0.3**, 초기 캐릭터 강도 **1.3**, 초기 경계 분리 **0.5**입니다. 기존 Anima 기본값은 유지합니다. SDXL에서는 Anima의 초기 공통 0.05·캐릭터 1.7·경계 0.9를 그대로 쓰면 화면이 칸처럼 갈라질 수 있습니다.

좌표는 프롬프트 영역을 정하며 정확한 인원·자세를 보장하지 않습니다. 특히 다인·격자 배치에는 중복 인물, 외형 혼합과 칸 분리가 생길 수 있습니다. SDXL Refiner·인페인트 모델·외부 attention 패치·ControlNet은 지원하지 않습니다. 생성 메타데이터는 SDXL 엔진으로 표시되며 이미지 로더로 복원할 수 있습니다. [방법과 실제 시험 기록](docs/sdxl-validation.md)


## Krea 2 / MOSS-Image 실험 지원

두 모델의 기본 지원이 포함된 최신 ComfyUI가 필요합니다. `Load CLIP`에 `krea2` 또는 `moss_image`가 없으면 ComfyUI와 해당 환경의 의존성을 먼저 업데이트하세요. 모델 선택만으로 샘플링 설정이 자동 변경되지는 않습니다.

| 모델 | 예제 | 텍스트 인코더 / VAE | 시작 설정 |
| --- | --- | --- | --- |
| Krea 2 Turbo | [2인 워크플로](examples/two-characters-krea2.json) | Qwen3-VL 4B, `krea2` / Qwen Image VAE | 8스텝 · CFG 1 · Euler + simple |
| MOSS-Image SFT | [2인 워크플로](examples/two-characters-moss.json) | Qwen3.5 9B, `moss_image` / Flux2 VAE | 50스텝 · CFG 3 · Euler + simple |

MODEL·CLIP·VAE와 기존 캐릭터 파이프를 연결합니다. 공통 칸에는 장면을, 캐릭터 칸에는 각자의 외형과 행동을 자연어 문장으로 적으세요. Krea 2 Turbo의 CFG 1에서는 공통 네거티브가 생성에 영향을 주지 않습니다. MOSS는 이 예제에서 ComfyUI 기본 CFG를 사용하며 공식 파이프라인의 네거티브 분기 22번 레이어 생략은 적용하지 않습니다.

샘플러는 **2~100스텝**을 받습니다. Anima·SDXL의 기존 30스텝 기본값은 유지합니다. 두 새 모델에서도 XY는 프롬프트 영역이며 정확한 인원·자세·복잡한 상호작용을 보장하지 않습니다. 이번 지원 범위는 T2I이며 참조 이미지 편집과 새 모델의 디테일러 품질은 검증 범위에 포함하지 않습니다. 모델 파일·사용 조건·시험 범위는 [지원 문서](docs/krea-moss-validation.md)를 보세요.


## 로컬 멀티캐릭터 디테일러

Manager에서 **ComfyUI-Impact-Pack**, **ComfyUI-Impact-Subpack**을 설치하고, **ComfyUI의 Python 환경**에서 `requirements-detailer.txt`를 설치한 뒤 재시작하세요. SAM은 선택 기능이며 사용할 모델을 별도로 설치해야 합니다. 일부 태거는 선택 시 안내되는 추가 의존성이 필요합니다.

[생성 → 디테일러 예제](examples/two-characters-detailer-anima.json)를 불러오면 됩니다. 생성에 사용하는 MODEL·CLIP·VAE(LoRA 포함)를 디테일러에도 연결하고, 샘플러의 `image`와 `character_pipe`를 이어 주세요. **RS 감지 콤바인 로더**, **RS 캐릭터 태거 로더**도 연결합니다. 기존 이미지라면 **RS MultiCharacter Load Image**의 이미지와 파이프를 바로 연결할 수 있습니다.

처음에는 기본 얼굴 SEGM·WD ViT v3·**보정 강도 0.25**로 시작하세요. 기본 화면에는 보정 강도·시드·자동 저장을 두고, 크롭·마스크·매칭·샘플링 설정은 상세 옵션에 넣었습니다. SEGM이 선택되면 BBOX·SAM은 로드하지 않습니다. SEGM을 OFF로 하면 BBOX 단독 또는 BBOX+SAM을 사용합니다. OFF 모델은 실행하지 않습니다. 기존 `ultralytics/segm`, `ultralytics/bbox`, `sams` 폴더의 모델도 목록을 새로 고치면 선택할 수 있습니다.

태거는 캐릭터를 고르는 용도이며 보정에는 **사용자가 입력한 원래 프롬프트**를 사용합니다. 홀·요철 채우기는 기본 적용입니다. 각 크롭은 원본에서 가져오고 수정 영역이 겹치지 않도록 처리합니다. 확신하기 어려운 매칭은 원본을 보존하며 이유를 보고서에 남깁니다. 점수가 높아도 잘못 연결할 수 있으므로, 특히 외형이 비슷하면 보고서의 캐릭터 번호와 결과를 확인하세요. 파이프는 **최대 10명**, 보정 영역은 **기본 10개·최대 64개**입니다. **처리수가 많을수록 품질을 보장하지 못합니다.**

자동 저장은 원래 생성 정보와 별도의 보정 이력을 PNG/WebP에 보존합니다. 워크플로 저장이 필요하면 기본 이미지 저장 노드를 사용하세요. PNG·무손실 WebP는 적용 마스크 밖 픽셀을 보존하지만, 손실 WebP는 압축 때문에 픽셀이 바뀔 수 있습니다. 현재 실제 보정 검증은 Anima 기준이며 다른 모델 계열은 아직 확인하지 않았습니다. [검증 기록](docs/detailer-validation.md)


## 샘플러·스케줄러 선택

설치된 ComfyUI의 샘플러와 스케줄러를 **모두 선택**할 수 있습니다. 첫 실행은 아래 기본 조합으로 시작하고, 다른 느낌이 필요하면 나머지 두 조합도 시도해 보세요. 노드의 선택창 도움말에도 같은 조합을 적었습니다.

| 용도 | 샘플러 | 스케줄러 | 이번 시험에서 확인한 점 |
| --- | --- | --- | --- |
| 기본 시작점 | `euler_ancestral` | `sgm_uniform` | 캐릭터 특징과 공통 배경이 선명함 |
| 다른 구도 시도 | `euler` | `linear_quadratic` | 특징을 유지하면서 서로 마주 앉는 요청을 반영 |
| 선명한 대안 | `dpmpp_2m_sde_gpu` | `beta` | 두 인물과 머리·옷·컵을 잘 구분. 마주 앉기 대신 나란히 배치됨 |

비교 조건은 **Anima Base v1.0·2인 카페 장면·한 시드·1536×768·30스텝·CFG 4·LoRA 없음**입니다. 45×9=405조합 모두 실행됐지만, 이미지 품질까지 모두 통과한 것은 아닙니다. 위 추천도 여러 장면에서의 성공률이나 순위를 뜻하지 않습니다.

샘플러와 스케줄러는 각각 직접 선택하며, 추천 밖의 조합도 실행할 수 있습니다. 이름에 추천 표시를 붙이거나 다른 값으로 자동 교체하지 않습니다. 기본값은 `euler_ancestral + sgm_uniform`입니다. 선택지는 설치된 ComfyUI 버전에 따라 달라집니다.

일부 CFG++ 조합은 이번 고정 조건에서 품질이 나빴습니다. **낮은 CFG·적은 스텝으로 재시험한 결과는 없으므로 미지원으로 단정하지 않습니다.** 현재 샘플러는 2~100스텝·CFG 1~20을 받습니다. 위 Anima 추천은 기존 30스텝 시험 기준이며 CFG++의 낮은 CFG·적은 스텝 회복 여부는 미검증입니다. [전수 시험과 추천 근거](docs/sampler-combinations.md)

## 이미지에서 복원

**RS MultiCharacter Load Image**에서 원본 PNG/WebP를 선택하고 `character_pipe`를 샘플러에 연결합니다. 이미지의 공통·캐릭터 문장과 좌표가 적용됩니다. `use_image_settings`를 켜면 시드·크기·샘플링·영역 설정도 복원하며, 끄면 그 값들은 샘플러에서 지정합니다.

모델·LoRA·CLIP·VAE는 직접 연결해야 합니다. 파일명과 강도는 메타데이터에 기록하지만 자동 교체하지 않습니다. 이 기능은 문장과 시드로 재생성하며 I2I가 아닙니다. NAI V4 형식 문장도 읽을 수 있으나 NAI 설정을 로컬 설정으로 쓸 수는 없으므로 이 경우 `use_image_settings`를 끄세요.

## 확인된 범위

- 지원하는 Anima·SDXL·Krea 2·MOSS 모델로 한 번에 1장입니다. 샘플러는 T2I, 디테일러는 마스크가 있는 크롭의 img2img를 수행합니다. SD1.5·Flux·ControlNet·외부 attention 패치는 지원하지 않습니다.
- 입력은 최대 10명입니다. 실제 생성 시험은 Anima 1~6명, SDXL 2~6명, Krea 2·MOSS 2~4명입니다. **처리수가 많을수록 품질을 보장하지 못합니다.** 가로 배치가 비교적 잘 맞으며, 새 모델의 2×2 성공 사례도 일반적인 성공률을 뜻하지 않습니다.
- 좌표는 프롬프트 영역입니다. 정확한 인물 위치나 인원수 보장은 아닙니다. 1명은 전 화면이 한 영역이므로 좌표 이동 효과가 없습니다.
- 두 줄·격자 배치는 인물이 늘거나 빠지는 실패가 큽니다. 여러 번 생성해 고를 필요가 있습니다.
- 리저널 샘플러는 캐릭터별 네거티브를 저장·복원만 하며 생성 시 명확한 오류를 표시합니다. 샘플러에는 공통 네거티브를 사용하세요. 디테일러는 매칭된 캐릭터의 개별 네거티브도 사용할 수 있습니다.
- 리저널 샘플러는 2~100스텝을 받으며 Anima·SDXL 기본값은 30입니다. 디테일러의 스텝 수는 별도로 조절합니다. 눈색·옷·손·소품·복잡한 상호작용은 틀릴 수 있습니다.

[전체 설명](README.md) · [구조와 메타데이터](docs/architecture.md) · [실제 검증 기록](docs/validation.md)
