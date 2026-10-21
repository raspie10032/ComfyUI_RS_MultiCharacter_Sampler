# Experimental character image reference / 실험적 이미지 참조 / 実験的画像参照

**Supported, NOT RECOMMENDED · 지원하지만 권장하지 않음 · 対応していますが非推奨**

This optional feature transfers broad visual cues, not a character's exact identity.
Use a character LoRA when available. SDXL/Illustrious can lose clothing details and
oversaturate colors. More references, arbitrary masks, model variants and LoRA
combinations have not received the same coverage as the two-person trials.

## Connect

`Character Prompt → Character Image Reference → Position / LoRA → Finalize → Sampler`

Role order is free: references bind to the same character number as Prompt,
LoRA and Position. Add one Reference node per image, connect a normal ComfyUI
Load Image output, and choose the number. Only active character slots survive
Finalize; text slots cannot have image references. Point, box and mask geometry
come from the existing Position/Mask nodes. No external IP-Adapter patch node is
needed; model family selection happens inside this sampler.

- Resolution: **64–1024, step 64, default 384**. Resize the longest edge and keep
  aspect ratio; smaller inputs are enlarged. Encoder padding does not crop the image.
- Strength: **0–2, default 0.6**. Larger is not always better. The exchange trials
  used FLUX.1 **0.1**, SDXL **0.5**, FLUX.2/3 **1.5**, others **0.6**. These are
  experiment settings, not universal presets.
- OFF / strength 0: no encoder, adapter or edit weight is loaded or downloaded.
- This is **Sampler-only**. Detailer keeps its existing prompt/LoRA behavior and
  does not apply image references.
- PNG/WebP metadata records reference number, hash, resolution and strength, **not
  the image**. Load Image restores ordinary generation settings; reconnect the
  original reference images to reproduce referenced generation.

## Backends and dependencies

Install `requirements-reference.txt` with the Python used by ComfyUI, then restart.
Basic generation and importing this extension do not require optional reference
packages. Downloads occur only during sampling with an active reference; the
Sampler's progress panel shows the file and download progress. Model licenses
are separate; pinned source repositories are listed in `reference_assets.json`.

| Family | Applied reference path | Resolution behavior |
|---|---|---|
| Anima | learned IP-Adapter residual + cross-attention helper LoRA | square padded, variable SigLIP2 grid; 384 = 576 tokens |
| SD1.5 | learned IP-Adapter Plus | pre-resized image, then native fixed 224px CLIP-Vision grid; 16 adapter tokens |
| SDXL / Illustrious | SDXL IP-Adapter Plus | same fixed-grid restriction; quality is inconsistent |
| FLUX.1 | Redux image conditioning with regional attention priors | fixed SigLIP grid; selection does not proportionally reduce tokens |
| FLUX.2 / FLUX 3 | native reference latents with regional attention | reference latent grid follows padded resolution |
| Krea 2 | separately downloaded edit LoRA + reference latents / vision text | reference latent grid follows resolution |
| MOSS | separately downloaded edit LoRA + reference latents | reference latent grid follows resolution |

Reference routing is available with `regional` layout. `moss_native` rejects active
references instead of silently mixing two conditioning paths. Model architecture,
matching text encoder and VAE requirements still apply. Arbitrary foreign attention
patches are not made compatible by this feature.

## 한국어

**캐릭터의 큰 특징을 유도하는 실험 기능이며 권장하지 않습니다.** 참조마다 이미지
한 장과 캐릭터 번호를 지정하고 기존 조립 파이프에 연결하세요. 프롬프트·LoRA·위치
노드와 연결 순서는 자유입니다. 참조 모델은 활성 참조로 생성할 때만 내려받으며
처음에는 파일이 커서 오래 걸릴 수 있습니다. `requirements-reference.txt`가 필요합니다.
참조 해상도는 긴 변 기준 64px 단위이며, SD/Redux 인코더는 내부 고정 크기를 사용하므로
해상도를 낮춰도 토큰 수가 비례해서 줄지는 않습니다. 저장 메타데이터에는 이미지가
없으므로 재생성하려면 원본 참조를 다시 연결해야 합니다. 디테일러에는 적용하지 않습니다.

## 日本語

**大まかな外見を誘導する実験機能で、推奨しません。** 画像1枚とキャラクター番号を
指定し、既存の組み立てパイプへ接続してください。役割ノードの接続順は自由です。
`requirements-reference.txt`が必要です。参照用モデルは有効な参照で生成するときだけ
取得します。解像度は長辺基準・64px単位ですが、SD/Reduxは内部で固定グリッドを使います。
保存メタデータに参照画像は含まれません。再現時は元の画像を接続してください。
Detailerには適用しません。

## Experiment report

Comparison images, per-run settings, hashes and limitations are downloadable from
[0.2.5 Release attachments](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases/tag/v0.2.5).
The report bundle is **not tracked in git** and is not included in `git clone`,
source archives or Registry packages. `export-ignore` alone would not exclude a
tracked report from cloning, so the report itself lives in Release assets.
