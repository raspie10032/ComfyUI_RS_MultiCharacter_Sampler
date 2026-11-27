# SPDX-License-Identifier: GPL-3.0-only
"""Install pinned ComfyUI model files on first use."""
import hashlib
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from .runtime_control import check_interrupted


def ensure_model_file(folder, name, url, size, sha256):
    import folder_paths

    path = folder_paths.get_full_path(folder, name)
    if path:
        return path

    target = Path(folder_paths.get_folder_paths(folder)[0]) / name
    temporary = None
    try:
        check_interrupted()
        target.parent.mkdir(parents=True, exist_ok=True)
        logging.info("RS: downloading %s", target.name)
        digest, received = hashlib.sha256(), 0
        with NamedTemporaryFile(dir=target.parent, prefix=".rs-model-", suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urlopen(url, timeout=30) as response:
                while chunk := response.read(256 * 1024):
                    check_interrupted()
                    received += len(chunk)
                    if received > size:
                        raise ValueError("Unexpected file size")
                    digest.update(chunk)
                    output.write(chunk)
        check_interrupted()
        if received != size or digest.hexdigest() != sha256:
            raise ValueError("Download failed SHA-256 verification")
        path = folder_paths.get_full_path(folder, name)
        if path:
            return path
        temporary.replace(target)
        folder_paths.filename_list_cache.pop(folder, None)
        return str(target)
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"Could not install {target.name} from Hugging Face ({error}). "
            f"Check the connection and retry, or place the file in models/{folder}/{name}."
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
