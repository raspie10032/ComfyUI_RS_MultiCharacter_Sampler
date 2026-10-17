# SPDX-License-Identifier: GPL-3.0-only
"""Keep original causes visible with a short, searchable error code."""


def user_error(code, error_type, message):
    return error_type(f"[RS MultiCharacter / {code}] {message}")
