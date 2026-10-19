# 0.2.2 Nieun / 니은 / ニウン

## 한국어

FLUX.1 Schnell·Dev, FLUX.2 Klein 4B·Base 4B·9B·Dev,
FLUX 3 Klein·Base의 네이티브 리저널 생성과 로컬 마스크 디테일러를 추가합니다.
기존 역할별 캐릭터 파이프와 STRING 입력은 그대로 사용합니다.

- FLUX.1/2의 독립 텍스트 위치와 FLUX 3의 초기 텍스트 블록·flow-map 처리를 지원합니다.
- FP8/INT8 모델의 캐릭터별 LoRA, 합쳐진 Q/K/V 레이어와 FLUX 3 LoRA 이름 변환을 보완했습니다.
- `flux_guidance`를 CFG와 별도로 설정하고 이미지 메타데이터에 저장·복원합니다.
- 모델별 FLUX 프리셋 8개와 [UI/API 예제](../examples/flux)를 제공합니다.
- 패키지와 샘플러 이름을 **0.2.2 니은**으로 갱신했습니다. 노드 ID는 유지합니다.

현재 모델을 지원하는 ComfyUI로 업데이트하고 모델·텍스트 인코더·VAE를 준비하세요.
예제에 맞는 프리셋을 적용한 뒤 모델 파일을 직접 선택합니다. 모델 다운로드는
패키지에 포함되지 않습니다. 업데이트 후 ComfyUI를 재시작하고 화면을 새로고침하세요.

실제 가중치 시험: 8종의 2인 생성·좌우 문장 교환·디테일러, 4종의 LoRA 16건,
5종의 이미지 설정 복원, 4종의 두 캐릭터+HELLO 배치, Anima·SDXL 회귀 생성을 완료했습니다.
Python 141개와 JavaScript 시험 파일 5개가 로컬에서 통과했습니다.

캐릭터별 LoRA의 영향은 다른 영역으로 퍼질 수 있으며 FLUX 3 Base에서 반대쪽 변화가
더 컸던 사례가 있습니다. 모든 변형의 실제 LoRA 시험을 완료한 것은 아닙니다.
태거가 불확실한 얼굴은 디테일러에서 건너뜁니다. FLUX Fill/Control·참조 이미지 편집·
GGUF는 이번 지원 범위에 포함되지 않습니다. 정확한 인원수·철자·외형을 보장하지 않습니다.
[시험별 증거와 한계](flux-validation.md)를 확인하세요.

## English

Nieun adds native regional generation and local masked detailing for eight FLUX.1,
FLUX.2 and FLUX 3 variants. It includes independent regional text positions,
FLUX 3 text/flow-map handling, packed FP8/INT8 regional LoRA fixes, embedded guidance
with metadata replay, eight FLUX presets and model-specific UI/API examples.
Existing modular character pipes and node IDs remain compatible.

Use a ComfyUI version that supports your model and supply its weights, text encoder
and VAE. Select the corresponding example/preset, restart ComfyUI after updating,
and refresh the frontend. Model weights are not bundled.

All eight variants completed actual two-person generation, caption swaps and
detailing. Trained LoRA trials cover four variants, replay covers five, and mixed
HELLO layouts cover four. Local checks passed 141 Python tests and five JavaScript
files. Regional LoRA can affect other regions; one FLUX 3 Base case changed the
opposite side more. Uncertain face matches are retained. Fill/Control, reference
editing and GGUF are outside the verified scope. See the [validation report](flux-validation.md).

## 日本語

ニウンでは FLUX.1・FLUX.2・FLUX 3 の8モデルでネイティブ領域生成とローカル
マスクディテーラーに対応します。領域別テキスト位置、FLUX 3の初期テキスト処理と
flow-map、FP8/INT8の領域別LoRA修正、内蔵ガイダンスの保存・復元、FLUXプリセット8種と
モデル別UI/API例を追加しました。既存のキャラクターパイプとノードIDは継続して使えます。

モデルに対応したComfyUIと拡散モデル・テキストエンコーダー・VAEを用意し、
例とプリセットを選んでください。更新後はComfyUIを再起動し、画面を再読み込みします。

実際の8モデルで2人生成・文章交換・ディテーラーを確認しました。学習済みLoRAは4種、
設定復元は5種、HELLO混合配置は4種で試験済みです。ローカルのPython 141件と
JavaScript 5ファイルが通過しました。LoRAの影響が別領域に広がる場合があり、
FLUX 3 Baseでは反対側の変化が大きい例もありました。不確実な顔は保持します。
Fill/Control・参照画像編集・GGUFは検証範囲外です。[詳細と制限](flux-validation.md)。
