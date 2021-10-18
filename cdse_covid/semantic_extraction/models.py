from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class AMRLabel:
    label_id: str
    graph: Any
    alignments: Any


@dataclass
class SRLabel:
    label_id: str
    labels: Mapping[str, str]


@dataclass
class WikidataQnode:
    qnode_id: str
    label: str
    description: Optional[str] = None
    score: Optional[float] = None
    from_query: Optional[str] = None