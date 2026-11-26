# SPDX-License-Identifier: GPL-3.0-only
"""Resolve image selections inside the ComfyUI directory chosen by the widget."""
from pathlib import Path, PureWindowsPath


def resolve_image_path(filename, *, annotated=True):
    import folder_paths

    invalid = 'Select an existing image inside the selected ComfyUI directory.'
    if not isinstance(filename, str) or not filename or '\x00' in filename:
        raise ValueError(invalid)
    directory = None
    if annotated:
        filename, directory = folder_paths.annotated_filepath(filename)
    relative = Path(filename)
    windows = PureWindowsPath(filename)
    if not relative.parts or relative.is_absolute() or windows.anchor or '..' in windows.parts:
        raise ValueError(invalid)

    try:
        root = Path(directory or folder_paths.get_input_directory()).resolve()
        path = (root / relative).resolve()
        if path.is_relative_to(root) and path.is_file():
            return path
    except (OSError, RuntimeError, ValueError):
        pass
    raise ValueError(invalid)
