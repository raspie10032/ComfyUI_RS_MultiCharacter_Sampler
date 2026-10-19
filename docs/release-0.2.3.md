# 0.2.3 Digeut / 디귿 / ディグッ

## 한국어

캐릭터별 LoRA 실행 경로를 최적화하고 노드 설명 UI를 추가합니다.

- **RS Character LoRA → 적용 모드**에서 **일반 적용 / 정밀 적용**을 선택합니다. 선택은 해당 파이프 전체에 적용됩니다.
- **일반 적용:** 지원되는 Anima·SDXL 선형 LoRA는 기본 모델의 레이어 계산을 공유하고 영역별 변화량을 적용합니다. 정밀 방식과 구도·표정·의상 세부가 달라질 수 있으며 특징이 다른 영역으로 퍼질 수 있습니다.
- **정밀 적용:** LoRA 설정마다 독립적으로 모델을 계산합니다. 지원되는 작은 행렬 최적화로 반복 가중치 합성 비용을 줄입니다. 서로 다른 설정이 많을수록 느려지며, 이름이 더 좋은 그림이나 완벽한 분리를 보장하지는 않습니다.
- 기본값과 모드가 없는 기존 워크플로·이미지는 **정밀 적용**입니다. 일반에서 미지원 모델·어댑터는 이유를 기록하고 정밀로 처리합니다. 실행 오류는 오류로 전달합니다.
- 모드와 캐릭터 LoRA 설정을 PNG/WebP 생성 정보에 저장·복원합니다. 디테일러는 두 모드 모두 매칭된 캐릭터를 정밀 방식으로 처리합니다.
- 주요 노드 하단에 선택에 따른 설명창을 추가했습니다. 설명은 한국어·일본어·영어를 지원하며 입력이나 저장값으로 들어가지 않습니다.
- 조절 항목에 마우스를 **2초** 올리면 짧은 설명을 표시합니다. 이동·드래그·스크롤 등으로 닫히며 ComfyUI의 툴팁 설정을 따릅니다.

같은 장비의 ILXL 2인·30스텝 단일 측정에서 기존 가중치 교체 83.47초,
최적화된 독립 계산 13.62초, 레이어 공유 8.36초였습니다. 텍스트 인코딩·저장을
제외한 샘플링 시간으로, 일반적인 속도 배율이나 메모리 절감을 보장하지 않습니다.
여러 캐릭터 LoRA의 추가 41장 비교와 실제 분할 노드 파이프 실행·이미지 복원도
확인했습니다. 특징 섞임이 없다는 정량적 검증은 아닙니다.
[시험 조건·결과·한계](shared-lora-experiment.md)를 확인하세요.

업데이트 후 ComfyUI를 재시작하고 브라우저를 새로고침하세요. 노드 ID는 유지합니다.
기존 모양을 출발점으로 삼으려면 정밀을, 지원 LoRA의 속도를 우선 비교하려면
일반을 선택하세요. 일반/정밀 모두 생성 결과는 시드·모델·프롬프트에 따라 달라집니다.

## English

Digeut adds **Normal / Precision** to RS Character LoRA and carries the choice through
the character pipe and PNG/WebP metadata. Normal shares layer calculations for supported
Anima/SDXL linear LoRAs. Precision retains independent predictions and uses low-rank
optimization where supported. Existing workflows and images default to Precision.
Unsupported Normal configurations fall back to Precision with a recorded reason;
runtime failures remain errors. The detailer uses Precision for each matched character.

Normal changes the algorithm and can change character details or spread features between
regions. Precision does not guarantee better artwork or perfect isolation. One local
ILXL two-character, 30-step comparison measured 83.47 s with native weight switching,
13.62 s with independent low-rank execution and 8.36 s with shared layers. These are
individual sampling measurements, not general speed or memory guarantees. See the
[conditions, additional character comparisons and limits](shared-lora-experiment.md).

Selection-dependent help panels and concise **two-second hover** hints support English,
Korean and Japanese. Display-only help is excluded from saved inputs. Hints respect the
ComfyUI tooltip preference and close on leaving, dragging or scrolling. Restart ComfyUI
and refresh the frontend after updating. Node IDs remain compatible.

## 日本語

ディグッでは RS Character LoRA に**通常適用 / 精密適用**を追加しました。
設定はキャラクターパイプ全体に適用され、PNG/WebPから復元できます。通常は対応する
Anima・SDXL線形LoRAのレイヤー計算を共有し、精密は独立した予測と対応する小行列
最適化を使用します。旧ワークフローとモードを持たない画像の初期値は精密です。
通常の非対応構成は理由を記録して精密に切り替えます。実行エラーはそのまま通知します。
ディテイラーはどちらの選択でも各キャラクターを精密方式で処理します。

通常は計算方法が異なるため、顔・服・構図が変わり、別領域へ特徴が広がる場合も
あります。精密も画質や完全な分離を保証しません。ILXLの2人・30ステップの単回測定は
従来83.47秒、独立した小行列方式13.62秒、共有方式8.36秒でした。一般的な速度や
メモリ削減の保証ではありません。[試験条件・追加比較・制限](shared-lora-experiment.md)。

主要ノードの選択説明欄と、**2秒のホバー**で表示する短い説明を日本語・韓国語・英語で
追加しました。説明は保存入力に含まれません。ComfyUIのツールチップ設定に従い、
移動・ドラッグ・スクロールなどで閉じます。更新後はComfyUIを再起動し、画面を再読み込み
してください。ノードIDは維持しています。
