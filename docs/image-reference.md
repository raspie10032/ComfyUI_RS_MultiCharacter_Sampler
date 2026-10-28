# Experimental character image reference / 실험적 이미지 참조 / 実験的画像参照

**Supported, NOT RECOMMENDED · 지원하지만 권장하지 않음 · 対応していますが非推奨**

This optional feature transfers broad visual cues. Exact face identity, small
accessories and separation in overlapping regions are not guaranteed. Prefer a
character LoRA when available. Reference processing adds model weights, memory
and generation time.

## Connect

`Character Prompt → Image Reference → Position / LoRA → Finalize → Sampler`

Building-node order is free. One Reference node binds one image to the same
character number used by Prompt, LoRA and Position. Use ordinary Load Image
outputs. Finalize discards disabled/out-of-range characters. Text regions cannot
have references. Existing point, box and silhouette masks select the target region.
No external IP-Adapter/model-patch node is needed for this input.

- **Resolution:** 64–1024 in 64px steps, default 384. Resize the longest edge while
  retaining aspect ratio. Native VAE backends align to model grids; SD encoders
  use their fixed internal grid. Anima reference-frame encoding also follows the
  target canvas grid, so this control is not a universal token/memory budget.
- **Strength:** 0–2, default 0.6. Start low; stronger references can copy poses,
  distort colors or compete with character LoRAs. The updated native paths have
  different strength semantics from Redux/IP-Adapter: old values are retained,
  but they do not reproduce old pixels.
- **OFF / strength 0:** loads/downloads no reference weights for that character.
- **Sampler only:** the detailer retains its prompt/LoRA behavior and ignores
  references. Basic generation requires no optional reference dependencies.
- **Metadata:** saves reference number, fingerprint, resolution and strength,
  not image pixels. Reconnect source images after loading generation metadata.

## Model-specific paths

Install `requirements-reference.txt` using ComfyUI's Python and restart. Weight
downloads happen only when sampling with active references, with node progress.
Model licenses are separate. Sources and revisions are in `reference_assets.json`.

| Family | Reference processing | Requirements and limits |
|---|---|---|
| **Anima** | ElectronGirl clean reference frames with the optimized RS regional attention | Automatically loads the pinned reference adapter. The common Image Reference node works; no extra MODEL adapter is required. Reference text K/V cache defaults OFF. Progressive resolution is supported. |
| **Krea 2** | Identity Edit **v2 r64**, image-grounded per-character text and clean VAE source tokens | Preserves source aspect ratio and uses the upstream `[text, references, target]` order. References sit beside the target in position space. Models without the matching vision text encoder are unsupported. |
| **FLUX.1** | Native Kontext reference latents with per-character routing | **Select a Kontext checkpoint** with its matching CLIP/T5 and VAE. Ordinary Dev/Schnell are not trained as Kontext; this node does not switch checkpoints automatically. Redux is no longer used for this input. |
| **FLUX.2 / FLUX 3** | Native reference latents with per-character routing | Keep source aspect ratio, align to VAE grid and share repeated attention-prior rows. Variant-specific encoders and VAE remain required. |
| **SD1.5** | Existing IP-Adapter Plus | Unchanged backend; fixed 224px CLIP-Vision grid. Quality is experimental. |
| **SDXL / Illustrious** | Existing SDXL IP-Adapter Plus | Unchanged backend; fixed encoder grid. Clothing and colors can drift. |
| **MOSS** | Existing experimental edit-LoRA reference path | Unchanged backend. This update does not add CharRef or claim reference quality improvements for MOSS. |

Only `regional` layout accepts this input. `moss_native` rejects active image
references. Foreign attention patches are not made compatible automatically.

A target region reads its own reference directly; overlaps can read both. Later
self-attention and the shared scene can still transfer features between people.
This is regional guidance, not a guarantee of isolated character identities.

The advanced **Anima Reference Frame** and **Anima Character Reference** nodes are
also available for explicit adapter/guidance controls. Use either the automatic
numbered input or an explicit global reference image; do not mix a global image
with numbered references. See [Anima adapter controls](anima-reference-frame.md).

## 한국어

기존 이미지 참조 노드의 연결은 유지됩니다. **Anima는 최적화한 참조 프레임,
Krea 2는 Identity Edit v2, FLUX는 네이티브 참조**를 사용합니다. Anima는 별도
모델 어댑터 노드를 연결하지 않아도 전용 가중치를 자동으로 준비합니다.
**FLUX.1은 Kontext 체크포인트를 직접 선택**하세요. 일반 Dev/Schnell이 자동으로
Kontext가 되는 것은 아닙니다. MOSS·SD1.5·SDXL 참조 방식은 유지합니다.

참조 번호는 프롬프트·위치·마스크·LoRA와 같게 맞추세요. 참조끼리 겹치면 특징이
섞일 수 있습니다. 해상도는 긴 변 기준 64px 단위이며 모델에 따라 실제 내부 토큰
수가 달라집니다. 참조 원본은 메타데이터에 저장하지 않으며 디테일러에는 적용하지
않습니다. 처리 시간이 늘고 기존 버전과 결과가 달라질 수 있습니다.

## 日本語

既存の画像参照ノードの接続を維持し、Animaは参照フレーム、Krea 2はIdentity
Edit v2、FLUXはネイティブ参照へ切り替えます。FLUX.1はKontextモデルを選択して
ください。MOSS・SD1.5・SDXLの参照方式は維持します。番号をPrompt・Positionと
合わせてください。重なりでは特徴が混ざる場合があります。画像はメタデータに
含まれず、Detailerには適用しません。

## References

- [Anima Ref Adapter](https://github.com/ElectronGirl/ComfyUI-Anima-Ref-Adapter),
  Apache-2.0; adapted source license in `ANIMA-REF-ADAPTER-LICENSE`.
- [Krea 2 Edit](https://github.com/lbouaraba/comfyui-krea2edit), Apache-2.0;
  adapted source license in `KREA2EDIT-LICENSE`.
- [Krea 2 Identity Edit weights](https://huggingface.co/conradlocke/krea2-identity-edit).
- FLUX native image-reference processing is provided by the installed ComfyUI;
  use the matching model's license and intended reference recipe.

Full experiment reports and images remain external release assets; they are not
bundled into git installations. Integration evidence is summarized in
[the replacement validation report](reference-replacement-validation.md).
