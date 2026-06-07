"""Load and validate the YAML configuration into a simple dotted-access object."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml


class Config(dict):
    """A dict that also supports attribute access and nested-dict wrapping."""

    def __getattr__(self, name: str) -> Any:
        try:
            value = self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
        return Config(value) if isinstance(value, dict) else value

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def load_config(path: str | None = None) -> Config:
    """Load config.yaml. Defaults to the file next to the project root."""
    if path is None:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "config.yaml")
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw)
