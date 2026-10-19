# Per-character LoRA — Zeta

The optimization clone exposes **normal / precision** on **RS MultiCharacter LoRAs**.
The choice travels through the building and character pipes to the sampler, applies
to every slot, and is saved/restored with image metadata. A description panel below
the LoRA settings updates with the selected mode in English, Korean or Japanese.
Precision is the compatibility default for existing workflows. Detailer samples
one matched character at a time using precision in either mode.
The description below of independent predictions applies to precision. Normal shares
intermediate layers for supported Anima/SDXL linear adapters, which changes the
algorithm. See [mode selection and evidence](shared-lora-experiment.md).

Use **0.1.7 Zeta Fix or later** for Anima with dynamic VRAM. Version 0.1.6 could
save the correct LoRA selections while applying them to an unused model instance.
The fix resolves the actual inference layers for each call and retains the shared
small-factor backend. [Controlled comparisons and scope](release-0.1.7.md).

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
Native ComfyUI conditioning hooks evaluate each distinct model-LoRA combination; spatial
masks combine the resulting positive **and negative** predictions before CFG. The
coordinate/box masks use the existing feather and overlap policy. An uncovered box
background or text box uses the incoming model, without additional character LoRAs.
Identical model-LoRA combinations share a hook group. Model weights are restored by
ComfyUI after the sampling call, including error/interruption cleanup. Supported
Anima LoRAs instead use the factor-only path below without patching base weights.

CLIP LoRA applies when encoding that character's positive prompt. Common positive,
common negative and text-region prompts use the incoming CLIP. The sampler retains
its existing limitation that per-character negative captions are metadata for the
detailer rather than independently sampled regional negatives.

The detailer uses the LoRA of the character selected by its normal matching step.
It samples one crop at a time using that character's selected LoRA backend and CLIP; it retains
the existing ownership mask and ambiguous-match skip behavior.

There is no extra full checkpoint per slot, but there are extra forward passes and
weight changes. In the initial Anima 1024×768/30-step test, a baseline/global-LoRA
generation took about 30 seconds and two distinct regional LoRAs took about 147
seconds. A subsequent paired test measured 150–156 seconds with weight hooks versus
about 66 seconds with the Anima factor-only path below. These are measurements from
one local setup, not general performance ratios.
The fallback uses ComfyUI's low-memory hook mode, avoiding cached full patched
weights per combination. File tensors and CLIP patches still consume memory.

### Factor-only execution

Ordinary Anima and SDXL Linear LoRAs automatically use ComfyUI's native **Bypass LoRA**
implementation: `W(x) + strength * up(down(x))`. Small factor tensors are shared
between slots using the same file, including different strengths. It avoids storing
merged full-size weights and repeatedly synthesizing them when switching regions.
Distinct LoRA combinations still need separate model predictions; this does not
combine multiple characters into one model evaluation.

All model patches in a file must qualify. Older cores without bypass,
DoRA/LoHa/LoKr/diff patches, convolutional adapters and multi-GPU clones retain
native weight hooks. Supported FLUX linear/quantized adapters retain the existing
FLUX bypass path; unsupported packed checkpoints report an error. CLIP LoRA still
uses the existing CLIP patch path. Bypass selection is automatic in precision mode.

Factor device copies are released after sampling, including errors or cancellation.
Each prediction restores temporary forward dispatch, also on partial setup failure.
The ordinary model, original file tensors and temporary activations still use memory.
Changed floating-point operation order can change pixels even at the same seed;
old metadata records the same LoRA settings, not a bit-identical legacy backend.
The two rank-32 test LoRAs retain about 175 MiB of factor data instead of a potential
6.56 GiB full merged-weight cache. That cache was already disabled in the old
low-memory path; this is not a measured 6.56 GiB reduction in the current runtime.
See [measured scope and limitations](regional-lora-bypass-validation.md).

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

Anima의 일반 Linear LoRA는 작은 행렬을 직접 계산하는 Bypass 경로를 자동으로
사용합니다. 같은 파일은 강도가 달라도 행렬을 공유하고, 큰 합성 가중치 캐시는
만들지 않습니다. 다른 모델·DoRA 등 확장 형식·양자화·다중 GPU는 기존 Hook으로
처리합니다. 서로 다른 LoRA 조합마다 예측하는 비용은 남고, 연산 순서가 달라
이전 버전과 같은 시드에서도 픽셀이 달라질 수 있습니다.

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

Anima の通常の Linear LoRA は、小さい行列を直接計算する Bypass 経路を自動で
使用します。同じファイルは強度が異なっても行列を共有し、大きな合成済み重みを
キャッシュしません。他のモデル、DoRA 等の拡張形式、量子化、複数 GPU は従来の
Hook を使用します。組合せごとの予測は必要で、演算順序の変更により同じシード
でも旧バージョンとはピクセルが異なる場合があります。

## Example and validation

[Two-character Anima workflow](../examples/zeta/two-character-loras-anima.json)
uses the same prompts, seed and LoRA strengths as the AB comparison. Select matching
local model and LoRA filenames before running; the model files are not included.
[Validation scope, measurements and limitations](regional-lora-validation.md).
