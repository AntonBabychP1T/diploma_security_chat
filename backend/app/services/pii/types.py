from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

ValueValidator = Callable[[str], bool]


@dataclass(frozen=True)
class PatternSpec:
    type_name: str
    pattern: str
    group_index: int = 0
    flags: int = 0
    priority: int = 0
    specificity: int = 0
    context_keywords: Tuple[str, ...] = ()
    context_window: int = 28
    value_validator: Optional[ValueValidator] = None


@dataclass(frozen=True)
class MatchCandidate:
    type_name: str
    start: int
    end: int
    value: str
    priority: int
    specificity: int
