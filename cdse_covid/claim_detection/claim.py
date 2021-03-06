"""Claim module."""
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union
from uuid import uuid4

from cdse_covid.semantic_extraction.mentions import (
    Claimer,
    ClaimSemantics,
    WikidataQnode,
    XVariable,
)

TOKEN_OFFSET_THEORY = "token_offset"


def create_id() -> str:
    """Create UUID id using the first 8 letters."""
    return str(uuid4())[:8]


@dataclass
class Claim:
    """A claim as documented by GAIA Nov 12, 2021."""

    claim_id: str
    doc_id: str
    claim_text: str
    claim_sentence: str
    claim_span: Tuple[str, str]
    claim_template: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    x_variable: Optional[XVariable] = None
    x_variable_identity_qnode: Optional[WikidataQnode] = None
    x_variable_type_qnode: Optional[WikidataQnode] = None
    claimer: Optional[Claimer] = None
    claimer_identity_qnode: Optional[WikidataQnode] = None
    claimer_type_qnode: Optional[WikidataQnode] = None
    claim_date_time: Optional[str] = None
    claim_location: Optional[str] = None
    claim_location_qnode: Optional[WikidataQnode] = None
    claim_semantics: List[ClaimSemantics] = field(default_factory=list)
    theories: MutableMapping[str, Any] = field(default_factory=dict)

    def add_theory(self, name: str, theory: Any) -> None:
        """Add a theory to the claim obj."""
        self.theories[name] = theory

    def get_theory(self, name: str) -> Optional[Any]:
        """Get an existing theory by *name*."""
        return self.theories.get(name)

    def get_offsets_for_text(
        self, text: Optional[str], tokenizer: Any
    ) -> Optional[Tuple[int, int]]:
        """Get the character offsets of the given string based on its claim span."""
        if not text:
            return None
        tokens_to_offsets: Dict[str, List[Tuple[int, int]]] = self.get_theory(  # type: ignore
            TOKEN_OFFSET_THEORY
        )
        if not tokens_to_offsets:
            logging.warning("No tokens -> offsets mapping for claim `%s`.", self.claim_sentence)
            return None
        text_tokens = tokenizer(text.strip())
        text_split = [token.text for token in text_tokens]
        # If there is only one token, simply grab the first span
        if len(text_split) == 1:
            offsets_list = tokens_to_offsets.get(text_split[0])
            if offsets_list:
                return offsets_list[0]
            else:
                logging.warning(
                    "Could not find char offset info for token '%s' in claim sentence `%s`",
                    text_split[0],
                    self.claim_sentence,
                )
                return None
        else:
            first_token = text_split[0]
            last_token = text_split[-1]
            first_offsets_list = tokens_to_offsets.get(first_token)
            if not first_offsets_list:
                logging.warning(
                    "Could not find char offset info for token '%s' in claim sentence `%s`",
                    first_token,
                    self.claim_sentence,
                )
                return None
            first_offsets_list.reverse()
            last_offsets_list = tokens_to_offsets.get(last_token)
            if not last_offsets_list:
                logging.warning(
                    "Could not find char offset info for token '%s' in claim sentence `%s`",
                    last_token,
                    self.claim_sentence,
                )
                return None
            # Find the first combination of spans that makes sense
            for first_offsets in first_offsets_list:
                for last_offsets in last_offsets_list:
                    first_idx = first_offsets[0]
                    last_idx = last_offsets[1]
                    if first_idx < last_idx:
                        return first_idx, last_idx
            logging.warning(
                "Could not find char offsets for string '%s' in claim sentence `%s`",
                text,
                self.claim_sentence,
            )
            return None

    @staticmethod
    def to_json(
        obj: Any, classkey: Optional[str] = None
    ) -> Union[List[MutableMapping[str, Any]], MutableMapping[str, Any], Any]:
        """Convert claim obj into a JSON mapping."""
        if isinstance(obj, dict):
            data = {k: Claim.to_json(v, classkey) for (k, v) in obj.items() if k != "theories"}
            return data
        elif hasattr(obj, "_ast"):
            return Claim.to_json(obj._ast())  # pylint: disable=protected-access
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [Claim.to_json(v, classkey) for v in obj]
        elif hasattr(obj, "__dict__"):
            data = dict(
                [
                    (key, Claim.to_json(value, classkey))
                    for key, value in obj.__dict__.items()
                    if not callable(value) and not key.startswith("_") and key != "theories"
                ]
            )
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
        else:
            return obj
