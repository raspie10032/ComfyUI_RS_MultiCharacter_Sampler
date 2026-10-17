# SPDX-License-Identifier: GPL-3.0-only
"""Local detection geometry and disjoint mask repair. No generation API imports."""
from types import SimpleNamespace
import numpy as np
from PIL import Image
from .errors import user_error
from .image_utils import tensor_to_pil
from .runtime_control import check_interrupted

def _detect(detector, image, threshold, dilation, crop_factor, drop_size=10):
    check_interrupted()
    if detector is None:
        return []
    segs = detector.detect(
        image, threshold, dilation, crop_factor, drop_size=drop_size, detailer_hook=None
    )
    return list(segs[1]) if segs else []

def _center(box):
    x0, y0, x1, y1 = box
    return ((x0 + x1) / 2, (y0 + y1) / 2)

def _crop_box(box, width, height):
    x0, y0, x1, y1 = box
    return (max(0, int(x0)), max(0, int(y0)), min(width, int(x1)), min(height, int(y1)))

def _context_crop(image, bbox, factor):
    x, y = _center(bbox)
    half_w = (bbox[2] - bbox[0]) * factor / 2
    half_h = (bbox[3] - bbox[1]) * factor / 2
    return image.crop(
        _crop_box((x - half_w, y - half_h, x + half_w, y + half_h), *image.size)
    )

def _mask_array(mask, *, allow_batch=False):
    """Return a finite 0..1 numpy mask without depending on a torch import."""
    if hasattr(mask, "detach"):
        mask = mask.detach().cpu().numpy()
    array = np.asarray(mask)
    if allow_batch:
        if array.ndim == 2:
            array = array[None, ...]
        if array.ndim != 3:
            raise user_error("DETAIL_MASK_INPUT", ValueError, "detail_mask must be [H,W] or [B,H,W].")
    else:
        if array.ndim == 3 and array.shape[0] == 1:
            array = array[0]
        if array.ndim != 2:
            raise user_error("DETAIL_MASK_INPUT", ValueError, "A detector region must contain one 2D cropped_mask.")
    if min(array.shape[-2:]) < 1 or not np.isfinite(array).all():
        raise user_error("DETAIL_MASK_INPUT", ValueError, "Detail masks need positive spatial dimensions and finite values.")
    # SAM3 individual_masks=True returns [0,H,W] when no objects are detected.
    if allow_batch and array.shape[0] == 0:
        return array.astype(np.float32, copy=False)
    array = array.astype(np.float32, copy=False)
    if array.min() < 0 or array.max() > 1:
        raise user_error("DETAIL_MASK_INPUT", ValueError, "Detail mask values must stay between 0 and 1.")
    return array

def _expanded_crop(bbox, width, height, factor):
    x, y = _center(bbox)
    half_w = max(1.0, bbox[2] - bbox[0]) * factor / 2
    half_h = max(1.0, bbox[3] - bbox[1]) * factor / 2
    return _crop_box((x - half_w, y - half_h, x + half_w, y + half_h), width, height)

def _native_crop_mask(seg, crop_region):
    if not hasattr(seg, "cropped_mask") or seg.cropped_mask is None:
        raise user_error(
            "DETAIL_MASK_INPUT", ValueError, "The selected SEGM detector did not provide cropped_mask data."
        )
    array = _mask_array(seg.cropped_mask)
    x0, y0, x1, y1 = crop_region
    expected = (y1 - y0, x1 - x0)
    if array.shape != expected:
        array = np.asarray(
            Image.fromarray(array, mode="F").resize(
                (expected[1], expected[0]), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        )
    return np.clip(array, 0, 1)

class RepairedDetector:
    def __init__(self, bundle, *, closing=True, fill_holes=True, dilation=8, mask_threshold=0.3):
        self.bundle = bundle
        self.closing, self.fill_holes, self.dilation = closing, fill_holes, dilation
        self.mask_threshold = mask_threshold

    def detect(self, image, threshold, dilation, crop_factor, **kwargs):
        from .mask_repair import bounds, plan_masks
        check_interrupted()
        height, width = image.shape[1:3]
        bundle = self.bundle
        if bundle.segm_detector is not None:
            primary, source = bundle.segm_detector, "segm"
        else:
            primary, source = bundle.bbox_detector, "bbox"
        segments = _detect(primary, image, threshold, 0, crop_factor)
        masks, valid = [], []
        predictor = None
        if source == "bbox" and bundle.sam_model is not None and segments:
            from segment_anything import SamPredictor
            predictor = SamPredictor(bundle.sam_model)
            predictor.set_image(np.asarray(tensor_to_pil(image)))
        for seg in segments:
            check_interrupted()
            if not all(np.isfinite(v) for v in (*seg.bbox, *seg.crop_region)):
                raise ValueError("Detector returned invalid coordinates. / 감지 모델이 올바르지 않은 좌표를 반환했습니다.")
            bx0, by0, bx1, by1 = _crop_box(seg.bbox, width, height)
            x0, y0, x1, y1 = _crop_box(seg.crop_region, width, height)
            if bx1 <= bx0 or by1 <= by0 or x1 <= x0 or y1 <= y0:
                continue
            if predictor is None:
                mask = np.zeros((height, width), bool)
                if source == "bbox":
                    mask[by0:by1, bx0:bx1] = True
                else:
                    mask[y0:y1, x0:x1] = _native_crop_mask(seg, (x0, y0, x1, y1)) >= max(self.mask_threshold, 1e-6)
            else:
                predicted, _, _ = predictor.predict(box=np.array([bx0, by0, bx1, by1]), multimask_output=False)
                mask = np.asarray(predicted[0], dtype=bool)
                if mask.shape != (height, width):
                    raise ValueError("SAM mask dimensions differ from the image. / SAM 마스크 크기가 원본과 다릅니다.")
            masks.append(mask)
            valid.append(seg)
        raw = np.stack(masks) if masks else np.zeros((0, height, width), bool)
        _, repaired, reports = plan_masks(raw, repair_mode="closing" if self.closing else "off",
                                          fill_holes=self.fill_holes, dilation=self.dilation)
        result = []
        for seg, fixed, report in zip(valid, repaired, reports):
            # Include dilation even with crop_factor=1. Keep identity detection boxes unchanged.
            box = bounds(fixed) if fixed.any() else seg.bbox
            bx0, by0, bx1, by1 = box
            x0, y0, x1, y1 = _expanded_crop(seg.bbox, width, height, crop_factor)
            crop = (max(0, min(x0, bx0)), max(0, min(y0, by0)), min(width, max(x1, bx1)), min(height, max(y1, by1)))
            x0, y0, x1, y1 = map(int, crop)
            result.append(SimpleNamespace(bbox=seg.bbox, crop_region=(x0, y0, x1, y1),
                cropped_mask=fixed[y0:y1, x0:x1].astype(np.float32),
                repair_report={**report, "closing": self.closing, "fill_holes": self.fill_holes,
                               "dilation": self.dilation, "source": "sam" if predictor is not None else source,
                               "face_detector": source}))
        return (height, width), result
