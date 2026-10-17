# SPDX-License-Identifier: GPL-3.0-only
import numpy as np
from PIL import Image
import torch


def validate_single_image(image):
    if not isinstance(image, torch.Tensor) or image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] != 3:
        raise ValueError("Connect one RGB image [1,H,W,3]. / RGB 이미지 한 장을 연결해 주세요.")
    if min(image.shape[1:3]) < 1 or not torch.isfinite(image).all() or image.min() < 0 or image.max() > 1:
        raise ValueError("Image pixels must be finite values from 0 to 1. / 이미지 픽셀 값을 확인해 주세요.")


def tensor_to_pil(image):
    validate_single_image(image)
    return Image.fromarray((image[0].detach().cpu().numpy() * 255).astype(np.uint8))
