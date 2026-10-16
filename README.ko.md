# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0-alpha1 · Anima 전용 알파**입니다. 공통 프롬프트와 캐릭터별 프롬프트·XY를 전용 파이프로 전달하고, 로컬 모델 내부에서 영역별 attention을 조절합니다. RS NAI 확장이나 API 키는 필요 없습니다.

## 설치와 사용

ComfyUI-Manager에서 **RS MultiCharacter Sampler (Anima Alpha)**를 검색해 설치하거나 [Comfy Registry 페이지](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)를 이용하세요. 패키지 ID는 `comfyui-rs-multicharacter-sampler`입니다. 설치 후 ComfyUI를 재시작하세요. 새 항목이 아직 보이지 않으면 Manager 목록을 갱신하거나 Git으로 설치할 수 있습니다.

Git 설치는 이 저장소를 `ComfyUI/custom_nodes` 안에 복제하면 됩니다. 기존 Git 설치본이 있다면 중복 설치하지 말고 그 설치본을 업데이트하세요. 모델은 자동 다운로드하지 않습니다.

[워크플로가 포함된 원본 PNG](examples/two-characters-workflow.png)를 캔버스로 끌어다 놓거나 [2인 예제 JSON](examples/two-characters-anima.json)을 불러온 뒤 설치된 Anima 모델·텍스트 인코더·VAE를 선택하세요. 예제의 `Load CLIP` 타입은 `stable_diffusion`입니다. 일반 LoRA 로더를 모델과 샘플러 사이에 연결할 수 있습니다.

1. **RS MultiCharacter Prompts**에서 캐릭터 수와 각 문장을 작성합니다. 기본은 5칸, 최대 10칸입니다. 인원수를 줄이면 숨겨진 슬롯의 이전 문장은 생성에 들어가지 않습니다.
2. X/Y는 0~1이며 왼쪽 위가 `(0,0)`입니다. 같은 좌표의 슬롯은 번호순으로 좌우에 배치합니다.
3. **RS MultiCharacter Sampler**의 공통 문장에는 전체 인원·화풍·장면을, 캐릭터 칸에는 각자의 외형·행동을 씁니다. 시험에서는 캐릭터마다 `1girl` 또는 `1boy`를 썼습니다.
4. 우선 30스텝·CFG 4·Euler ancestral·SGM uniform 기본값으로 실행하세요. 시드의 실행 후 동작은 랜덤으로 바꿀 수 있습니다.
5. 자동 저장은 `output/RS_MultiCharacter`에 PNG 또는 WebP로 생성 정보와 함께 저장합니다. 워크플로는 넣지 않습니다. 워크플로도 필요하면 ComfyUI 기본 이미지 저장 노드를 쓰세요.

공유용 예제 PNG에는 ComfyUI `workflow`·`prompt` 메타데이터가 들어 있습니다. 샘플러의 일반 자동 저장에는 기존처럼 생성 정보만 들어갑니다.

## 이미지에서 복원

**RS MultiCharacter Load Image**에서 원본 PNG/WebP를 선택하고 `character_pipe`를 샘플러에 연결합니다. 이미지의 공통·캐릭터 문장과 좌표가 적용됩니다. `use_image_settings`를 켜면 시드·크기·샘플링·영역 설정도 복원하며, 끄면 그 값들은 샘플러에서 지정합니다.

모델·LoRA·CLIP·VAE는 직접 연결해야 합니다. 파일명과 강도는 메타데이터에 기록하지만 자동 교체하지 않습니다. 이 기능은 문장과 시드로 재생성하며 I2I가 아닙니다. NAI V4 형식 문장도 읽을 수 있으나 NAI 설정을 로컬 설정으로 쓸 수는 없으므로 이 경우 `use_image_settings`를 끄세요.

## 확인된 범위

- Anima 전용, 한 번에 1장, T2I만 지원합니다. 다른 모델 계열·ControlNet·attention 패치는 아직 지원하지 않습니다.
- 입력은 최대 10명, 실제 생성 시험은 1~6명입니다. **처리수가 많을수록 품질을 보장하지 못합니다.** 가로 배치가 비교적 잘 맞습니다.
- 좌표는 프롬프트 영역입니다. 정확한 인물 위치나 인원수 보장은 아닙니다. 1명은 전 화면이 한 영역이므로 좌표 이동 효과가 없습니다.
- 두 줄·격자 배치는 인물이 늘거나 빠지는 실패가 큽니다. 여러 번 생성해 고를 필요가 있습니다.
- 캐릭터별 네거티브는 저장·복원만 하며 생성 시 명확한 오류를 표시합니다. 현재는 공통 네거티브를 사용하세요.
- 현재 검증된 30스텝 스케줄을 고정 사용합니다. 눈색·옷·손·소품·복잡한 상호작용은 틀릴 수 있습니다.

[전체 설명](README.md) · [구조와 메타데이터](docs/architecture.md) · [실제 검증 기록](docs/validation.md)
