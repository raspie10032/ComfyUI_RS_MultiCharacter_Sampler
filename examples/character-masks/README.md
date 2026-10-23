# Character mask example

[Detailed guide / 한국어 / 日本語](../../docs/character-masks.md)

1. Put `character-1.png` and `character-2.png` in ComfyUI's `input` directory, or upload each through **Load Image (as Mask)**. Select the `red` channel.
2. Open `two-character-masks-anima.json` in ComfyUI. The `.api.json` file is for API clients.
3. Select your Anima model, compatible text encoder and VAE. The supplied filenames are examples; models are not included. No style LoRA is required.
4. Keep character IDs 1 and 2 matched to their Prompt rows. Mask 1 and Mask 2 connect along the building pipe before Finalize.
5. Adjust `scale`, `offset_x`, `offset_y` and `margin`. The colored diagram shows each character's approximate support and overlap. Scaling uses the canvas center; anything beyond the canvas is clipped.
6. Generate. Use the final black/white node preview or `region_mask` output to inspect the exact transformed masks. PNG/WebP autosave preserves the masks for **RS Load Image**.

For interactive placement, connect **Mask / Mask Drawing → Position → Finalize** so Position can see the upstream shapes. Its top selector chooses a numbered Point / Box / Mask; drag to move, use the corner or −/+ to resize boxes/masks. Position edits preserve the source mask and scale about the shape's own center. Undo and Reset selected are available. Builder execution is order independent, but its live editor reads upstream inputs; downstream masks appear in Finalize's guide.

한국어: 두 PNG를 기본 **Load Image (as Mask)**의 `red` 채널로 읽고, 편집용 JSON을 불러온 뒤 Anima 모델·텍스트 인코더·VAE를 선택하세요. 크기·이동·여유 폭은 마스크 노드에서 조절합니다. 캐릭터 번호와 Prompt 행을 맞추세요. 전체 캔버스를 유지하며 밖으로 나간 마스크만 자릅니다.

日本語: 2枚のPNGを標準 **Load Image (as Mask)** の`red`で読み、編集用JSONを開いてAnima・テキストエンコーダー・VAEを選択してください。マスクノードで倍率・移動・余白を調整し、Prompt行とキャラクター番号を合わせます。キャンバス外にはみ出したマスクだけを切り取ります。

These masks were drawn for this example and are available under the repository license. They are prompt guides, not pose controls: pose, hands, people count and exact composition can vary. Text still uses boxes. With MOSS select `regional` to retain silhouette shapes. Native JSON converts masks to their enclosing rectangles after placement.

Validation: the API example passed a real Anima generation at 1536×1024, 30 steps, Euler ancestral / SGM uniform. A separate Anima run confirmed scale 0.9 with position offsets. PNG metadata loaded through RS Load Image reproduced the original output pixel for pixel. PNG/WebP mask restoration, mixed point/box/mask routing, clipping, disabled-mask fallback and native-model CPU paths have automated coverage. Full trained-model generation across every supported family has not been tested for this feature.
