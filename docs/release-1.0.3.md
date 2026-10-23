# 1.0.3 Hangeul: MOSS native mask bounds

MOSS native layout now accepts character masks. It converts each finalized mask
to its enclosing rectangle and sends that rectangle through the existing native
JSON prompt path. Previously, a mask caused an error before generation.

Bounds include mask movement, scaling, margin and clipping at the canvas edge.
The original silhouette stays in the character pipe and image metadata. Native
JSON receives only the enclosing rectangle: detailed outlines and holes are not
preserved. Use `regional` when silhouette-shaped conditioning is required.

The sampler panel, mask help and tooltips explain the conversion in English,
Korean and Japanese. Explicit boxes retain their coordinates; point-only regions
still require `regional`. Layout defaults and the native JSON item labels are
unchanged.

## Validation and limits

The full Python suite ran against the installed ComfyUI core: 226 tests passed
and one existing core-dependent test skipped. All 10 JavaScript UI suites passed.
Regression tests cover irregular masks, moved and clipped masks, single-pixel
bounds, mixed masks and text boxes, preservation of the original mask, and the
localized notice appearing only for native layout. Existing mask validation
rejects empty masks before conversion. This release does not claim new image
quality validation: no new full-model image generation was performed for this
change.

## 한국어

MOSS 네이티브에서도 마스크를 사용할 수 있습니다. 이동·크기·여유 폭과
캔버스 밖 잘림을 반영한 최종 마스크를 외곽 사각형으로 변환합니다.
세부 모양과 구멍은 JSON에 반영되지 않으며, 원래 마스크는 파이프와
이미지 메타데이터에 보존됩니다. 모양을 유지하려면 `regional`을 쓰세요.
패널과 툴팁에도 이 차이를 안내합니다.

## 日本語

MOSSネイティブでもマスクを使用できます。移動・倍率・余白・キャンバス外の
切り取りを反映した最終マスクを外接矩形に変換します。細かい輪郭や穴はJSONに
反映されません。元のマスクはパイプと画像メタデータに保持します。
輪郭を維持する場合は `regional` を使用してください。パネルとツールチップにも
この違いを表示します。
