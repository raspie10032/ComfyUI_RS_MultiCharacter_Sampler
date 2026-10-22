# OpenPose mask example

Load **anima-hug.json** in ComfyUI. Choose your installed Anima model, compatible CLIP and VAE in the three loader nodes. `anima-hug-api.json` is the corresponding API-format prompt. Both start with body-part guidance OFF, baseline overlap separation and Euler ancestral / SGM uniform.

Two adult women are mapped to the source JSON people array, in that order. Select a person in Character Position, then drag or resize its mask. Adjust thickness in OpenPose Masks; optional body-part name guidance is described in [the guide](../../docs/openpose-mask-guides.md).

The embedded pose frame and `front-hug-frame.json` are the “front hug” frame from [andreszs/ComfyUI-OpenPose-Studio — poses/hugging.json](https://github.com/andreszs/ComfyUI-OpenPose-Studio/blob/main/poses/hugging.json). The upstream file was verified on 2026-10-22 with SHA256 `d61535868f4cb8fc8013fbd6a4dc3a30df5523f2cc59af2bfd654897e0055c44`. Pose data is distributed with its original [MIT license](POSE-DATA-LICENSE.txt). Extension code remains GPL-3.0-only.
