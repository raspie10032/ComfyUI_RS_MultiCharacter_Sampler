# Per-character LoRA — Zeta

In **RS MultiCharacter Prompts**, each active character has `characterN_lora`,
`characterN_lora_strength` (model), and `characterN_lora_clip_strength` (text encoder).
Choose an installed file from `models/loras`; subfolders are supported. `None` disables
that slot's LoRA. Strength controls appear after selecting a file. Text slots hide
these controls and never receive a character LoRA. Maximum region count remains 10.

Continue using the existing character pipe; no extra per-character loader nodes are
needed. A global style or acceleration LoRA can remain on the incoming MODEL/CLIP.
Slot LoRAs are added on top of that input. Use matching files for the model family.
MOSS 8-step and similar acceleration LoRAs belong on the global model loader.

The base model, checkpoint and global LoRA connections are still explicit workflow
inputs. Slot filenames and both strengths are saved with the character metadata in
PNG/WebP. Load Image restores them into the pipe, and the next sampler/detailer uses
matching local files. This works independently of `use_image_settings`, which controls
generation settings. Missing or incompatible LoRAs report an error rather than being
silently skipped. Old images/workflows without this extension use `None`.

## How it works and what it costs

The sampler keeps its existing character attention routing in each model evaluation.
Native ComfyUI weight hooks evaluate each distinct model-LoRA combination; spatial
masks combine the resulting positive **and negative** predictions before CFG. The
coordinate/box masks use the existing feather and overlap policy. An uncovered box
background or text box uses the incoming model, without additional character LoRAs.
Identical model-LoRA combinations share a hook group. Model weights are restored by
ComfyUI after the sampling call, including error/interruption cleanup.

CLIP LoRA applies when encoding that character's positive prompt. Common positive,
common negative and text-region prompts use the incoming CLIP. The sampler retains
its existing limitation that per-character negative captions are metadata for the
detailer rather than independently sampled regional negatives.

The detailer uses the LoRA of the character selected by its normal matching step.
It samples one crop at a time using that character's model hook and CLIP; it retains
the existing ownership mask and ambiguous-match skip behavior.

There is no extra full checkpoint per slot, but there are extra forward passes and
weight changes. In the initial Anima 1024×768/30-step test, a baseline/global-LoRA
generation took about 30 seconds and two distinct regional LoRAs took about 147
seconds. This is a measurement from one local setup, not a general performance ratio.
The implementation uses ComfyUI's low-memory hook mode, avoiding cached full patched
weights per combination. File tensors and CLIP patches still consume memory.

## Limits

- Regional LoRA is a spatial influence, not an isolated paint layer. Attention,
  diffusion and VAE decoding can carry changes across boundaries; exact containment
  or identity fidelity is not guaranteed. Feathered boundaries also blend influences.
- A single model hook is constant over the diffusion run. Existing step schedules
  continue controlling prompt routing; they do not change the slot LoRA strength.
- Choose one LoRA per character in this version. Compose a global stack upstream if
  needed. No automatic downloading or model-family conversion is performed.
- A LoRA that changes Anima's precomputed `llm_adapter` is rejected for slots; connect
  it globally. It cannot be correctly separated through denoising hooks alone.
- MOSS native layout uses one literal prompt encoding. Per-character CLIP LoRA
  requires `regional`, or CLIP strengths of zero in native mode.
- Node-level ComfyUI caching follows input filenames. If replacing a LoRA's contents
  under the same name, invalidate the graph/cache or restart ComfyUI before comparison.

## 한국어

캐릭터 노드 하단에서 **캐릭터 N LoRA**를 고르고 **모델 강도 / CLIP 강도**를
설정합니다. 파일을 선택하면 강도 입력이 나타납니다. `None`은 미사용이며 글자
영역에는 적용되지 않습니다. 기존 캐릭터 파이프만 연결하면 샘플러와 디테일러가
함께 사용합니다. 전체 스타일·가속 LoRA는 기존 전체 로더에 연결하세요.

PNG/WebP 메타데이터에 파일명과 두 강도가 저장됩니다. 이미지 로더로 복원하면
실행 시 같은 로컬 파일을 사용하므로, 다른 PC에서는 그 파일을 `models/loras`에
준비해야 합니다. 없는 파일·다른 모델 계열·지원하지 않는 텍스트 어댑터는 오류로
알려줍니다. 이전 이미지·워크플로는 미사용 상태로 열립니다.

서로 다른 LoRA가 늘면 계산도 늘어납니다. 상자로 완벽하게 잘라 붙이는 기능이
아니므로 영역 밖의 구도·색·배경에도 변화가 생길 수 있습니다. 정확한 캐릭터 재현과
분리 품질은 모델·LoRA·프롬프트마다 확인해야 합니다.

## 日本語

キャラクターノードで **キャラクター N LoRA** を選び、モデル強度と CLIP 強度を
設定します。`None` は無効です。文字領域には適用しません。既存の専用パイプで
Sampler と Detailer に渡します。全体の画風・高速化 LoRA は通常のローダーへ
接続してください。

PNG/WebP にファイル名と強度を保存し、画像ローダーから復元できます。同名の
ローカルファイルが必要です。不足・モデル不一致・未対応のテキストアダプターは
エラーを表示します。旧画像・旧ワークフローでは無効のまま動作します。
LoRA の組合せが増えるほど計算量も増えます。領域外への影響や境界の混ざりは
完全には防げません。

## Example and validation

[Two-character Anima workflow](../examples/zeta/two-character-loras-anima.json)
uses the same prompts, seed and LoRA strengths as the AB comparison. Select matching
local model and LoRA filenames before running; the model files are not included.
[Validation scope, measurements and limitations](regional-lora-validation.md).
