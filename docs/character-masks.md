# Character silhouette masks / 캐릭터 마스크 / キャラクターマスク

## 한국어

### 위치 노드에서 공통 배치 편집

배치도 **위쪽 선택기**에서 `1 · 포인트`, `2 · 박스`, `3 · 마스크`처럼 번호·종류를 고르세요. 선택한 영역만 움직입니다. 포인트는 드래그로 위치를 바꾸고, 박스는 드래그·오른쪽 아래 모서리로 이동·크기를 조절합니다. 마스크도 드래그하고 모서리나 **−/+**로 비율을 유지해 확대·축소합니다. 마스크는 자기 중심을 기준으로 확대되며, 캔버스 밖으로 나간 부분만 잘립니다. 원래 모양을 보관하므로 다시 안으로 옮기거나 **선택 배치 초기화**를 누르면 돌아옵니다. 전부 밖에 있으면 실행 전에 오류로 안내합니다.

번호와 프롬프트·LoRA의 연결은 고정됩니다. **되돌리기**와 워크플로 저장·재불러오기를 지원하며, 배치 편집은 원본 드로잉을 수정하지 않습니다. 파이프 실행 결과는 연결 순서와 무관합니다. 화면에서 마스크를 편집하려면 **마스크/드로잉 → Position → Finalize**로 연결하세요. 편집기는 앞에 연결한 모양을 읽고, 뒤에 연결한 마스크는 Finalize 배치도에서 확인합니다. 다른 노드에서 연결한 수치는 원본 입력에서 수정하고, 미준비 마스크는 먼저 실행하세요. 배치도는 축소된 가이드입니다.

### 이미지 위에 직접 그리기

`RS 캐릭터 마스크 그리기`에서 **참조 이미지 열기 → 번호 선택 → 그리기** 순서로 칠하세요. 참조 인물이 누구인지와 무관하게 1번 마스크에는 1번 프롬프트·LoRA가 적용됩니다. 별도 캐릭터 자동 인식이나 태거는 필요 없습니다.

- 그리기·지우개·되돌리기·선택 영역 지우기를 지원합니다. 번호를 바꾸면 다른 마스크를 편집합니다.
- 이동 도구로 드래그하거나 X/Y 비율과 크기를 조절합니다. 크기는 캔버스 중심 기준이며, 캔버스 밖으로 나간 부분만 잘립니다.
- 색 미리보기는 여유 폭을 포함한 적용 범위의 축소 표시입니다. 정밀한 포즈 고정은 아니며 생성된 팔다리를 잘라내지 않습니다.
- 조립 파이프의 어디에든 연결한 뒤 최종 파이프로 보내세요. 이 노드가 앞선 마스크 표를 대체하고, 빈 번호는 기존 XY·박스를 사용합니다. 개별 마스크로 덮어쓸 때는 뒤에 연결하세요.
- 참조 이미지는 **생성 입력으로 사용하지 않습니다**. 획·번호·이동·크기는 워크플로에, 적용 마스크는 생성 메타데이터에 저장됩니다. 참조 파일이 없어도 저장한 획으로 마스크를 복원합니다.
- 원본 비율을 유지하고 긴 변 최대 2048px로 드로잉 캔버스를 만듭니다. 가로세로가 매우 다른 출력에서는 같은 형태가 늘어나므로 같은 비율을 권장합니다.

텍스트 슬롯은 계속 위치 노드의 박스로 지정하세요. MOSS에서 사람 모양 마스크를 사용할 때는 `regional` 모드가 필요합니다.

`RS 캐릭터 마스크`는 사람 실루엣이나 직접 칠한 마스크를 **캐릭터 프롬프트가 읽히는 영역**으로 사용합니다. 기존 위치 노드의 점·사각형보다 자유롭게 팔·몸통·접촉 영역을 정할 수 있습니다. 별도 ControlNet 모델은 필요하지 않습니다. **포즈 고정 기능은 아니며**, 인원수·자세·손가락·원본 구도를 보장하지 않습니다.

1. 이미지 로더의 마스크 편집기에서 전체 캔버스에 영역을 그리거나, 외부 노드의 `MASK`를 준비합니다. 흰색은 캐릭터 영역, 검정은 바깥쪽입니다. 흑백 PNG라면 ComfyUI 기본 **Load Image (as Mask)** 노드에서 `red` 채널로 읽으세요. 일반 이미지 로더의 기본 MASK 출력은 알파 채널에서 계산하므로 불투명한 흑백 PNG가 빈 마스크로 읽힐 수 있습니다.
2. `RS Character Mask`를 추가하고 프롬프트 노드와 같은 **캐릭터 번호**를 고릅니다. 캐릭터마다 노드 하나와 마스크 한 장을 사용합니다.
3. `building_pipe`를 Prompt·LoRA·Position과 같은 줄에 연결한 뒤 Finalize → Sampler로 보냅니다. 역할 노드들의 순서는 자유입니다. 번호별로 마지막 마스크 설정을 사용하며, LoRA·위치 테이블을 바꾸어도 마스크는 유지됩니다.
4. `margin`은 **입력 마스크 해상도의 픽셀** 단위로 흰 영역을 넓힙니다. 기본 24px, 범위 0–128px입니다. 머리·옷·손을 맞대는 부분에 여유를 주세요. 이미 넓혀 둔 마스크에는 0을 사용합니다. `threshold`는 흑백 기준이며 기본 0.5입니다.
5. **크기 비율 `scale`**: 1.0 원래 크기, 0.5 절반, 2.0 두 배입니다 (0.05–4.0). 입력 캔버스 중심을 기준으로 가로세로 비율을 유지하며 확대축소합니다. **`offset_x` / `offset_y`**는 캔버스 가로/세로 대비 이동 비율입니다 (-1–1). 양수는 오른쪽/아래, 0.1은 10% 이동입니다. 확대축소 → 이동 → 여유 폭 순서로 적용합니다.
6. **캔버스 밖으로 나간 마스크는 그대로 잘라 씁니다.** 반대편으로 돌아오거나 안쪽에 들어오도록 다시 축소하지 않습니다. 생성된 인물의 머리·팔다리를 잘라내는 기능은 아닙니다. 전부 밖으로 나가거나 너무 작아지면 이동·크기를 고치라는 오류가 나옵니다.
7. 마스크·위치·최종 파이프의 **예상 배치도에 번호별 색과 겹치는 부분**을 표시합니다. 기본 Load Image (as Mask)에 직접 연결하면 이동·크기·여유 폭을 생성 전에 확인할 수 있습니다. 외부 가공 노드나 연결된 수치 입력은 실행 후 실제 적용 마스크를 표시하며, 입력 변경 시 이전 결과는 숨기고 실행을 안내합니다. 배치도는 축소한 안내도이므로 픽셀 단위 검사는 `region_mask` 출력 또는 실행 후 흑백 미리보기를 사용하세요.

입력 마스크 캔버스를 전체 출력 크기에 맞춥니다. 이동·크기 조절로 캔버스 밖으로 나간 흰 부분은 잘립니다. 마스크 이미지와 출력 이미지의 종횡비를 맞추세요. 한 장씩, 최대 4096×4096입니다. 회색은 연속 강도가 아니라 흑백으로 변환됩니다. 생성 해상도에서 사라질 정도로 작은 영역은 여유 폭을 늘리라는 오류로 중단합니다.

마스크가 있는 번호는 그 번호의 XY·BBOX 대신 마스크를 사용합니다. 끄면 XY·BBOX로 돌아갑니다. 다른 번호에는 좌표·사각형·다른 마스크를 섞어 쓸 수 있습니다. 겹치는 부분은 해당 캐릭터 문장을 함께 읽고, 모든 명시 영역 바깥은 공통 프롬프트를 읽습니다. 점 방식의 캐릭터도 있다면 남은 영역을 그 점들 사이에서 나눕니다. 전체 캐릭터·텍스트 합계는 기존과 같은 최대 10개입니다.

캐릭터별 LoRA와 함께 사용할 수 있습니다. 자동 저장 PNG·WebP에는 마스크 모양도 보존되며 RS Load Image가 파이프로 복원합니다. 파일 경로를 참조하지 않으므로 원래 마스크 파일이 없어도 복원할 수 있습니다. 워크플로 저장은 기본 Save Image를 사용하세요. 텍스트 영역은 계속 사각형을 사용하며, **MOSS native JSON은 마스크를 지원하지 않으므로 `regional`을 선택**하세요. 디테일러로 파이프를 전달할 수 있지만 얼굴 보정 마스크는 기존 감지 모델이 따로 만듭니다.

[기본 예제](../examples/character-masks)는 직접 그린 두 마스크와 API·편집용 워크플로를 제공합니다. 실제 생성 확인 범위와 한계는 예제 README에 적습니다.

## English

### Shared layout editing in Position

Choose a numbered **Point / Box / Mask above the layout**; dragging changes only that selection. Drag points and boxes to move them; use a box's bottom-right handle to resize. Masks move the same way and resize uniformly about their own center using the corner or **−/+**. Canvas overflow is clipped without destroying the source shape. Move it back or **Reset selected** to recover it; fully off-canvas masks produce an actionable error before generation. Numbers keep their Prompt/LoRA assignments. **Undo** and workflow reload preserve placement without changing the source drawing. Builder execution is order independent. For interactive editing, connect Mask / Mask Drawing → Position → Finalize: the editor reads upstream shapes; downstream masks appear in Finalize’s guide. Edit connected values at their source; run unknown masks first. The preview is a reduced guide.

**RS Character Mask** uses a painted mask or silhouette as the support of a character's prompt attention. It does not require a ControlNet model and does not guarantee exact pose, anatomy, composition or people count.

Connect one full-canvas `MASK` per character, match `character_id` to its Prompt row, and place the node anywhere on the building-pipe line before Finalize → Sampler. For opaque black/white PNGs, use core **Load Image (as Mask)** with channel `red`; ordinary Load Image derives its MASK from alpha and may return an empty mask. White selects the region. Keep the mask and output aspect ratios equal: the mask is resized to the full canvas without cropping.

`margin` expands the white area in **source-mask pixels** (default 24, range 0–128). Leave space for clothing, hair and interaction; use 0 for a previously expanded mask. `threshold` defaults to 0.5; gray is converted to binary support. The node previews the applied mask after running and also outputs it as `region_mask`. `scale` keeps the aspect ratio about the source-canvas center: 0.5 half, 1 original, 2 double (0.05–4). `offset_x`/`offset_y` move it by fractions of the canvas width/height (-1–1; positive right/down). Order: scale → shift → margin. Overflow is clipped, never wrapped or fitted back inside. This clips the mask, not generated body parts. Fully clipped masks fail with a correction message. Empty masks, batches and subpixel regions fail with actionable messages. Maximum input size is 4096×4096; large complex masks must fit the image metadata budget.

A mask overrides its character's XY/box regardless of builder order. Turn it off to restore XY/box. Repeating this node for the same number replaces that number's mask. Other characters retain their settings. Mix masks, points, boxes, text boxes and regional LoRAs within the existing ten-slot limit. Overlaps read the participating character captions; the background reads the common caption, or is partitioned among point characters when present. Mask, Position and Finalize show colored shapes and overlaps in their layout guides. A direct core Load Image (as Mask) connection previews changes before generation. Other MASK providers or connected controls use the executed result; changing upstream inputs hides stale results until another run. The small diagram is approximate; inspect the MASK output or executed monochrome preview for exact pixels.

PNG/WebP autosave stores the binary shapes, which RS Load Image restores without the original mask files. Editing workflows use ordinary Save Image. Text and **MOSS native JSON** still require boxes: select **regional** for masks. Detailer receives the pipe but continues using detector masks for face edits. [Examples and verification scope](../examples/character-masks).

## 日本語

### Positionで共通の配置編集

配置図**上の選択器**で番号と点・ボックス・マスクを選ぶと、選んだ領域だけ動きます。ドラッグで移動、ボックスは右下の角で拡縮。マスクも角や **−/+** で自身の中心を基準に縦横比を保って拡縮します。キャンバス外だけ切り取り、元の形は残るので戻すか**選択をリセット**で復元できます。全体が範囲外なら生成前に案内します。番号とPrompt/LoRAの対応は固定。**元に戻す**・ワークフロー再読み込みに対応し、元の描画は変更しません。実行結果は接続順に依存しません。画面でマスクを編集する場合は **Mask / Mask Drawing → Position → Finalize** の順で接続してください。エディタは上流の形を読み、下流のマスクはFinalizeの配置図で確認します。接続値は元で編集し、未準備マスクは先に実行します。図は縮小した目安です。

**RS キャラクターマスク**は、シルエットや描いたMASKをキャラクター文のattention領域に使います。ControlNetモデルは不要ですが、ポーズ・人数・手指・元の構図を保証しません。

Promptと同じキャラクター番号を選び、1人につきMASK1枚を接続します。組立パイプ上のPrompt・LoRA・Positionとの順序は自由で、最後にFinalize → Samplerへ渡します。不透明な白黒PNGは標準 **Load Image (as Mask)** の `red` チャンネルで読みます。通常のLoad ImageのMASKはアルファから作られるため、空になる場合があります。白が内側、黒が外側です。全キャンバスに切り抜かずリサイズするので、出力と縦横比を合わせてください。

`scale`はキャンバス中央を基準に縦横比を保つ倍率です（0.5半分、1元、2倍；0.05～4）。`offset_x`/`offset_y`は幅・高さに対する移動比率です（-1～1、正は右・下）。倍率→移動→余白の順に適用し、キャンバス外は切り取ります。折り返しや自動縮小はせず、生成人物の体を切る機能ではありません。全体が外に出ると修正を案内します。`margin`は元マスクの画素単位の余白です（初期24、0～128）。髪・服・接触に余白を残し、拡張済みなら0にします。`threshold`は初期0.5で白黒化し、グレーを連続強度としては扱いません。実行後にノード内へ適用マスクを表示し、MASK出力からも確認できます。最大4096×4096、1枚ずつです。空や小さすぎる領域は生成前にエラーにします。

マスクは同じ番号のXY・ボックスを置き換えます。OFFで元の位置設定に戻り、同じ番号を繰り返すと最後の設定を使います。他の番号の点・矩形・マスク、領域別LoRAと併用でき、文字を含め合計10領域までです。重なりは双方の文を読み、明示領域の外は共通文を読みます。点のキャラクターがあれば残りを点同士で分割します。Mask・Position・Finalizeの配置図に色付きの形と重複を表示します。標準Load Image (as Mask)への直接接続は生成前に更新し、他のMASKノードや接続値は実行結果を使います。入力を変えた古い結果は隠し、再実行を案内します。配置図は縮小した目安で、正確な画素はMASK出力か実行後の白黒プレビューで確認します。

PNG・WebPの自動保存には形も含め、RS Load Imageで元ファイルなしに復元できます。ワークフロー保存は標準Save Imageを使います。文字領域と **MOSS native JSONは矩形専用**なので、マスク使用時は `regional` を選択してください。ディテーラーは引き続き検出モデルの顔マスクを使います。[例・検証範囲](../examples/character-masks)。
