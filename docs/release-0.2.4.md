# 0.2.4 Rieul / 리을 / リウル

Released from the character-shape-masks development candidate on 2026-10-20 (KST). Package and runtime version: **0.2.4**. Previous 0.2.3 Digeut notes remain in [their original release report](release-0.2.3.md).

## 한국어

- **RS 캐릭터 마스크 그리기:** 참조 이미지를 밑에 놓고 번호를 선택해 캐릭터별 영역을 직접 칠합니다. 그리기·지우개·되돌리기·선택 영역 지우기를 지원합니다. 참조 이미지는 화면 표시용이며 생성 이미지나 i2i 입력으로 전달하지 않습니다.
- **RS 캐릭터 마스크:** 외부 MASK를 같은 번호의 캐릭터에 적용합니다. 여유 폭·흑백 기준·크기 비율·가로세로 이동을 조절합니다. 번호와 프롬프트·LoRA 연결은 위치 변경 후에도 유지됩니다.
- **공통 배치 편집:** Position 배치도 위 선택기에서 포인트·박스·마스크 번호를 선택합니다. 드래그로 위치를 바꾸고 박스·마스크 모서리로 크기를 조절합니다. 마스크는 비율을 유지하며 자기 중심으로 확대축소하고, −/+·되돌리기·선택 배치 초기화를 제공합니다.
- **캔버스 밖 마스크만 자르기:** 원래 모양을 보존하므로 다시 안으로 옮기면 복구됩니다. 생성된 머리·팔다리를 자르지 않습니다. 마스크 전체가 밖으로 나가거나 너무 작으면 수정 방법을 오류로 안내합니다.
- **미리보기·복원:** 번호별 색과 겹침을 표시하며 PNG·WebP 자동 저장에는 적용 마스크가 들어갑니다. RS Load Image에서 원본 마스크 파일 없이 파이프로 복원합니다. 워크플로 저장은 ComfyUI 기본 Save Image를 사용합니다.

연결 예: **캐릭터 프롬프트 → LoRA → 마스크 그리기 → 캐릭터 위치 → 최종 파이프 → 샘플러**. 실행 결과는 역할 노드 순서와 무관하지만, 위치 편집기에서 마스크를 보며 움직이려면 마스크/드로잉을 위치 노드 앞에 연결하세요. 최대 10개 캐릭터·텍스트 영역은 기존과 같습니다. 텍스트는 박스를 사용합니다.

마스크는 자연스러운 배치를 유도하는 attention 영역입니다. 포즈·인원수·체형·손의 접촉을 정확히 고정하지 않습니다. MOSS는 `regional`을 사용하세요. `moss_native` JSON 배치는 실루엣 마스크를 지원하지 않습니다. 디테일러의 얼굴 보정 영역은 기존 감지 모델이 만듭니다.

## English

Adds **RS Character Mask Drawing** for numbered painting over a display-only reference and **RS Character Mask** for external MASK inputs. Both join the modular building pipe without changing existing prompt/LoRA assignments. The extension now registers twelve nodes; old saved workflows keep their original node IDs and input names.

Position's selector above the layout chooses one point, box or mask. Drag to move; resize boxes or uniformly scale masks using the corner handle. Mask −/+ controls, Undo and Reset selected preserve the source drawing. Only canvas overflow is clipped; moving the mask back recovers its shape. Fully clipped, empty or subpixel regions fail with guidance. External masks also support margin and threshold controls.

PNG and both WebP autosave modes preserve effective mask shapes for RS Load Image without the source mask file. The drawing and placement controls survive ordinary workflow save/reload. Reference images are guides in the editor, not generation inputs. For live mask placement, connect **Mask / Mask Drawing → Position → Finalize**; execution remains order independent, while the editor reads upstream data.

Masks guide prompt attention, not exact pose, anatomy, count or interaction. Text remains box-based. Select `regional` for MOSS silhouettes; native JSON layouts require boxes. Detailer still constructs its face-edit masks from detections. [Detailed usage](character-masks.md) · [Examples](../examples/character-masks).

## 日本語

**RS キャラクターマスク描画**で参照画像の上に番号別の領域を描き、**RS キャラクターマスク**で外部MASKを接続できます。参照画像は表示専用です。番号とPrompt/LoRAの対応を保ち、既存ワークフローのノードID・入力名は維持します。

Positionの配置図上で点・ボックス・マスクの番号を選び、ドラッグで移動します。角でボックスを拡縮し、マスクは自身の中心を基準に縦横比を保って拡縮します。−/+・元に戻す・選択配置のリセットに対応。キャンバス外だけを切り取り、元の形は残すので戻せます。全体が範囲外や小さすぎる場合は修正を案内します。

PNG・WebPの自動保存から元ファイルなしで形を復元できます。編集時は **Mask / Mask Drawing → Position → Finalize** の順が便利です。実行結果は役割ノードの順序に依存しません。マスクは領域誘導であり、ポーズ・人数・体型・手の接触を保証しません。文字は矩形を使い、MOSSのマスクは`regional`を選択してください。[使い方](character-masks.md) · [例](../examples/character-masks)。

## Validation scope

- **Release source tests:** 182 Python tests, 181 passed and 1 test for older cores without native bypass skipped because the installed core provides native bypass against the installed native ComfyUI CPU path. Nine JavaScript test files passed, including mask preview invalidation and numbered position editing. The two new UI suites are included in GitHub CI.
- **Browser evidence from the development candidate:** numbered selection, isolated point/box/mask dragging, resizing, undo/reset, canvas-overflow guidance and workflow reload were exercised in a dedicated browser session. This release changes version labels, documentation and CI coverage on top of that candidate.
- **Actual trained-model generation from the development candidate:** Anima Aesthetic v1.1 with the private RSC/MyMy 80:20 style LoRA at 1.0 completed two- and three-character mask trials. A 1344×1152, 30-step Euler ancestral / SGM uniform run moved mask 3 left by 0.15 and scaled it to 1.1. Rereading the saved PNG reproduced all finalized character settings and effective binary masks exactly. The example workflow also completed a separate Anima generation and metadata replay. These are limited execution/comparison observations, not a general success-rate estimate.
- **Other model families:** native CPU integration tests cover shape routing and sampling APIs, including SD1.5/SDXL and available native transformer paths. Full trained-model mask generations across every supported family have not been performed. Existing model-family compatibility does not prove exact silhouette control.
- **No pose guarantee:** some reference comparisons changed scale and relative depth while omitting the requested hand/sleeve contact. Third-party reference art and private model/LoRA weights are not bundled; example masks were drawn for this repository.

Reproduce source checks from the repository root:

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -v
node tests/test_mask_preview_ui.cjs
node tests/test_position_editor_ui.cjs
```

Use the Python environment of your ComfyUI installation. Native CPU fixtures validate APIs and routing with small synthetic models; they do not assess artwork quality. See [mask example setup and limits](../examples/character-masks/README.md) for the actual generation workflow.
