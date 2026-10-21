# 0.2.6 Bieup / 비읍 / ピウプ

## 한국어

Krea 2 Turbo FP8와 MOSS INT8에서 캐릭터별 LoRA를 켜면 발생하던
`weight_scale` 오류를 수정합니다. 일반 선형 LoRA를 기존 양자화 모델의
계산 결과에 더하는 경로로 적용하며 원본 가중치와 scale을 변경하지 않습니다.
비양자화 MOSS는 기존 가중치 Hook 경로를 유지합니다. 이 경로에서 처리할 수
없는 양자화 LoRA 형식은 샘플링 전에 모델 계열과 이유를 표시합니다.

- Krea2/Illustrious 캐릭터 LoRA 프리셋과 UI/API 워크플로 예제를 추가했습니다.
  예제의 모델·LoRA 파일명은 설치 환경에 맞게 선택해야 합니다.
- 기존 별도 서버 시험에서 9개 모델 구성마다 무적용·전역 LoRA·캐릭터 1·
  캐릭터 2·강도 0·제거 후의 6개 조건을 생성했습니다. Krea2 FP8와 MOSS INT8은
  수정 전 오류를 재현하고 수정 후 모두 생성했습니다.
- Illustrious를 제외한 시험 구성은 강도 0·제거 후에 무적용 이미지와 RGB
  픽셀이 일치했습니다. Illustrious는 LoRA를 쓰기 전 반복 생성에서도 차이가
  발생하여 픽셀 일치로 잔류 여부를 판정하지 않습니다.
- 릴리스 통합 검사: Python **190개 통과, 1개 조건부 제외**, JavaScript UI
  검사 **9개 통과**. 실제 생성 기록은 이 통합 검사와 별도로 수행한 결과입니다.

이번 생성 시험은 여러 시드의 캐릭터 재현율이나 영역 밖 무영향을 보장하지
않습니다. FLUX.3, GGUF, 캐릭터별 CLIP LoRA와 모든 변형 LoRA는 이번 시험
대상에 포함하지 않았습니다. 0.2.5의 이미지 참조 기능은 계속 실험적이며
권장하지 않습니다.

[시험 조건·결과·한계](character-lora-matrix-20261021.md) ·
[예제 워크플로](../examples/character-lora/README.md)

업데이트 후 ComfyUI를 재시작하고 브라우저를 새로고침하세요.
기존 노드 ID와 워크플로 연결은 유지합니다.

## English

Fixes the `weight_scale` error when applying per-character LoRA to Krea 2 Turbo
FP8 and MOSS INT8. Plain linear LoRA factors run alongside the original quantized
forward without replacing packed weights or scales. Full-precision MOSS keeps
its existing weight-hook path. Unsupported packed LoRA formats report the model
family and reason before sampling.

Adds Krea2/Illustrious character-LoRA presets and UI/API examples. Select filenames
that match your installation. Earlier isolated generation checks covered nine
model configurations with six controls each: none, global, character 1, character
2, zero, and removed. Krea2 FP8/MOSS INT8 failures were reproduced before the fix;
all six controls generated after it. Zero/removed matched baseline RGB pixels
except for Illustrious, whose fresh runs also differed before any LoRA use.

Release integration checks: **190 Python tests passed, one skipped; all nine
JavaScript UI suites passed**. These checks are separate from the earlier GPU
generation matrix. Results do not establish multi-seed identity accuracy or zero
spillover. FLUX.3, GGUF, per-character CLIP LoRA, and arbitrary adapter formats were
not tested in this matrix. Image references introduced in 0.2.5 remain experimental
and not recommended. Restart ComfyUI and refresh the browser after updating.

## 日本語

Krea 2 Turbo FP8・MOSS INT8でキャラクターLoRAを適用した際の
`weight_scale` エラーを修正しました。通常の線形LoRAを量子化モデルの
計算に加算し、元の重みとscaleを変更しません。非量子化MOSSは従来の
経路を維持します。未対応の量子化LoRA形式は生成前に理由を表示します。

Krea2/Illustrious向けプリセットとUI/API例を追加しました。ファイル名は
各環境に合わせて選択してください。既存の別サーバー試験では9モデル構成で
各6条件を生成し、Krea2 FP8・MOSS INT8の修正前エラーと修正後の生成を確認。
Illustrious以外は強度0・解除後のRGBが未適用と一致しました。Illustriousは
LoRA未使用の繰り返しでも差があり、一致による残留判定はできません。

リリース統合検査はPython **190件成功・1件スキップ**、JavaScript UI
**9件成功**。既存のGPU生成試験とは別の検査です。FLUX.3・GGUF・
キャラクター別CLIP LoRAや全派生形式、多数シードでの再現率は未検証です。
0.2.5の画像参照は引き続き実験的で推奨しません。更新後はComfyUIを再起動し、
ブラウザーを再読み込みしてください。
