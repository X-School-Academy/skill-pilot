"""JSON5 read/write helpers built on json-five.

Plain reads use ``json5.loads``. Writes that target files with comments should
use ``write_preserving_comments`` so json-five's model loader/dumper can retain
comments and whitespace on surviving nodes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json5
from json5.dumper import ModelDumper
from json5.loader import ModelLoader
from json5.model import (
    BooleanLiteral,
    DoubleQuotedString,
    Float,
    Identifier,
    Integer,
    JSONArray,
    JSONObject,
    JSONText,
    NullLiteral,
)

load = json5.load
loads = json5.loads
dumps = json5.dumps


def _escape_double(value: str) -> str:
    out: list[str] = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


def _build_node(value: Any):
    if value is None:
        return NullLiteral()
    if isinstance(value, bool):
        return BooleanLiteral(value=value)
    if isinstance(value, int):
        return Integer(raw_value=str(value))
    if isinstance(value, float):
        return Float(raw_value=repr(value))
    if isinstance(value, str):
        return DoubleQuotedString(
            characters=value, raw_value='"' + _escape_double(value) + '"'
        )
    if isinstance(value, list):
        node = JSONArray()
        node.values = [_build_node(v) for v in value]
        return node
    if isinstance(value, dict):
        node = JSONObject()
        node.keys = [
            Identifier(name=str(k), raw_value=str(k)) for k in value.keys()
        ]
        node.values = [_build_node(v) for v in value.values()]
        return node
    raise TypeError(f"Cannot serialize {type(value).__name__} to JSON5")


def _key_name(key) -> str | None:
    name = getattr(key, "name", None)
    if name is not None:
        return str(name)
    chars = getattr(key, "characters", None)
    if chars is not None:
        return str(chars)
    return None


def _copy_trivia(old, new):
    new.wsc_before = list(getattr(old, "wsc_before", []) or [])
    new.wsc_after = list(getattr(old, "wsc_after", []) or [])
    return new


def _reconcile(node, new_value):
    """Mutate ``node`` so its data equals ``new_value`` and keep overlapping trivia."""
    if isinstance(node, JSONObject) and isinstance(new_value, dict):
        existing: dict[str, tuple] = {}
        for k_node, v_node in zip(node.keys, node.values):
            name = _key_name(k_node)
            if name is not None and name not in existing:
                existing[name] = (k_node, v_node)

        sample_key_wsc_before = None
        sample_value_wsc_before = None
        if node.keys:
            sample_key_wsc_before = list(
                getattr(node.keys[-1], "wsc_before", []) or []
            )
        if node.values:
            sample_value_wsc_before = list(
                getattr(node.values[-1], "wsc_before", []) or []
            )

        new_keys = []
        new_values = []
        for k_new, v_new in new_value.items():
            sk = str(k_new)
            if sk in existing:
                k_node, v_node = existing[sk]
                new_keys.append(k_node)
                new_values.append(_reconcile(v_node, v_new))
            else:
                key_node = Identifier(name=sk, raw_value=sk)
                if sample_key_wsc_before is not None:
                    key_node.wsc_before = list(sample_key_wsc_before)
                value_node = _build_node(v_new)
                if sample_value_wsc_before is not None:
                    value_node.wsc_before = list(sample_value_wsc_before)
                new_keys.append(key_node)
                new_values.append(value_node)
        node.keys = new_keys
        node.values = new_values
        return node

    if isinstance(node, JSONArray) and isinstance(new_value, list):
        old = list(node.values)
        sample_wsc_before = None
        if old:
            sample_wsc_before = list(getattr(old[-1], "wsc_before", []) or [])
        replaced = []
        for i, v_new in enumerate(new_value):
            if i < len(old):
                replaced.append(_reconcile(old[i], v_new))
            else:
                fresh = _build_node(v_new)
                if sample_wsc_before is not None:
                    fresh.wsc_before = list(sample_wsc_before)
                replaced.append(fresh)
        node.values = replaced
        return node

    fresh = _build_node(new_value)
    return _copy_trivia(node, fresh)


def write_preserving_comments(
    path: Path | str,
    new_value: Any,
    *,
    indent: int = 2,
    trailing_newline: bool = True,
) -> None:
    """Write ``new_value`` to ``path`` as JSON5 while preserving comments."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if p.is_file():
        text = p.read_text(encoding="utf-8")
        model = json5.loads(text, loader=ModelLoader())
        if isinstance(model, JSONText):
            model.value = _reconcile(model.value, new_value)
            output = json5.dumps(model, dumper=ModelDumper())
        else:
            output = json5.dumps(new_value, indent=indent)
    else:
        output = json5.dumps(new_value, indent=indent)

    if trailing_newline and not output.endswith("\n"):
        output += "\n"
    p.write_text(output, encoding="utf-8")
