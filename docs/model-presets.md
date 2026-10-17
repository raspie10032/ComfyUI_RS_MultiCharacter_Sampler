# Model family presets

The Epsilon sampler has **Model family preset → Apply preset** controls. Select the preset that matches the connected model and intended layout, then press **Apply preset**. Selecting a name only previews its guidance; applying copies the values into the existing sampler controls. You can edit those controls afterward. The guidance reports whether the current values still match the preset.

| Preset | Steps / CFG | Sampler / scheduler | Initial common / character / separation |
|---|---|---|---|
| Anima — XY | 30 / 4 | Euler ancestral / SGM uniform | 0.05 / 1.70 / 0.90 |
| Anima — mixed | 30 / 4 | Euler ancestral / SGM uniform | 0.60 / 1.70 / 0.90 |
| SDXL / Illustrious — XY | 30 / 5.5 | Euler ancestral / normal | 0.30 / 1.30 / 0.50 |
| SDXL / Illustrious — mixed | 30 / 5.5 | Euler ancestral / normal | 0.15 / 1.50 / 0.90 |
| Krea 2 Turbo | 8 / 1 | Euler / simple | 0.60 / 1.20 / 0.35 |
| MOSS — base | 50 / 3 | Euler / simple | 0.60 / 1.20 / 0.35 |
| MOSS — 8-step LoRA | 8 / 3 | Euler / simple | 0.60 / 1.20 / 0.35 |
| SD1.5 — experimental | 30 / 7 | Euler ancestral / normal | 0.20 / 1.70 / 0.90 |

All presets also copy point feather **0.04**, common boost after step 3 **0.1**, boundary hold **3**, and boundary decrement **0.2**. These are initial values for the existing step schedule. The source of each preset is its published example; the [catalog](../web/model_presets.json) records the exact example path and values.

Presets change sampling and regional controls. **Model, CLIP, VAE and LoRA connections, prompts, character count, point/box layout, width, height, seed and saving choices stay under your control.** A preset does not identify or download the connected model. MOSS 8-step requires a separate matching LoRA connection; the tested LoRA strength is **0.7**. SD1.5 was tested at **768×512**. A preset does not change the canvas size.

The labels and guidance follow ComfyUI's English, Korean or Japanese language setting. After changing the interface language, reload the page to refresh these labels. Preset selection is saved as a node property, and the applied values use the ordinary sampler settings. Opening, reconnecting or executing a workflow never silently reapplies the preset. Custom workflows and API requests continue to use explicit settings; no new backend input is required.

## Conflicting controls

- Turn off **use_image_settings** before applying: enabled restoration uses settings stored in the input image. Prompts and characters from the image pipe still follow the existing image-loader behavior.
- Use **layout_method = regional**. These presets tune regional attention; MOSS native layout ignores these regional controls and needs its own settings.
- If a targeted value or either mode switch is connected to another node or converted to an input, convert it back to a widget before applying. External connections take precedence over widget values.
- If a required control, sampler or scheduler is unavailable, the sampler explains which one is missing and leaves all values intact.

## Evidence and limits

The XY presets come from the original model examples. Mixed presets use the [model-specific comparison settings](mixed-layout-tuning.md); MOSS 8-step uses the [MOSS mixed example](../examples/epsilon/moss-mixed.json). The SDXL presets are based on the documented Illustrious workflow, not a quality guarantee for all SDXL derivatives. SD1.5 remains a compatibility check for distinguishable people and visible lettering; natural anatomy and exact spelling are not established.

The prompt, seed and box placement also influence the image. Copying these numbers into a different scene does not guarantee the example result. Use the full examples to reproduce the documented comparisons.

See the [preset UI and real-generation validation record](model-presets-validation.md) for the checks performed on this feature.

## 한국어

샘플러 하단의 **모델 계열 프리셋 → 프리셋 적용**을 사용하세요. 이름을 고르면 안내만 바뀌고, 적용 버튼을 눌러야 스텝·CFG·샘플러·스케줄러·영역 강도가 바뀝니다. 이후 수동으로 수정할 수 있으며, 저장 후 다시 열어도 프리셋을 자동으로 덮어쓰지 않습니다. Anima·SDXL은 좌표용과 혼합 배치용이 따로 있습니다.

모델·LoRA 연결, 문장, 인원수, 좌표·상자, 해상도, 시드는 직접 설정합니다. MOSS 8스텝은 LoRA 강도 **0.7**을 별도로 연결해야 합니다. 이미지 설정 복원은 끄고 `regional`에서 사용하세요. 외부 입력 연결이나 사용할 수 없는 선택지가 있으면 전체 적용을 중단하고 이유를 표시합니다. SD1.5는 품질 보장 없이 구분과 실행을 확인한 시험값입니다. 언어를 바꾼 뒤 페이지를 새로고침하면 프리셋 표시도 바뀝니다.

## 日本語

サンプラー下部の **モデル系統プリセット → プリセットを適用** を使います。名前の選択だけでは値は変わらず、適用ボタンでステップ・CFG・サンプラー・スケジューラー・領域強度をコピーします。適用後の手動変更も可能で、保存したワークフローの再読み込み時に上書きしません。AnimaとSDXLには座標用と混合配置用があります。

モデル・LoRAの接続、プロンプト、人数、座標・枠、解像度、シードは個別に設定してください。MOSS 8ステップではLoRA強度 **0.7** の別接続が必要です。画像設定の復元をオフにし、`regional`で使用します。外部入力や利用できない選択肢があると、すべての適用を中止して理由を表示します。SD1.5は品質保証ではなく人物の区別と動作を確認した試験値です。言語変更後はページを再読み込みしてください。
