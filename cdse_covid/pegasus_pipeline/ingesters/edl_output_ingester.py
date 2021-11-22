"""Ingest EDL documents and convert them to workable internal format."""
import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import MutableMapping, Tuple


@dataclass
class EDLEntity:
    """Class for EDL Entity."""

    ent_id: str
    ent_type: str


@dataclass
class EDLMention:
    """Class for EDL Mention."""

    doc_id: str
    text: str
    mention_type: str
    span: Tuple[int, int]
    parent_entity: EDLEntity


def main(edl_output: Path, output: Path) -> None:
    """Run EDL Ingester."""
    mention_store: MutableMapping[str, MutableMapping[Tuple[int, int], EDLMention]] = defaultdict(
        dict
    )
    with open(edl_output / "merged.cs", "r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        all_entities = {}
        for line in reader:
            if len(line) == 3:  # We have ourselves a new entity
                _id = line[0].split("_")
                formatted_id = _id[-1]
                ent_type = line[2]
                if line[1] == "link":  # Not including links to Freebase right now
                    continue
                new_entity = EDLEntity(ent_id=formatted_id, ent_type=ent_type)
                all_entities[formatted_id] = new_entity
            elif len(line) == 5:  # We have ourselves a new mention
                ent_id = line[0].split("_")
                formatted_ent_id = ent_id[-1]
                mention_type = line[1]
                text = line[2]
                doc_and_span = line[3].split(":")
                doc = doc_and_span[0]
                span = doc_and_span[1].split("-")
                formatted_span = (int(span[0]), int(span[1]))
                new_mention = EDLMention(
                    doc_id=doc,
                    text=text,
                    mention_type=mention_type,
                    span=formatted_span,
                    parent_entity=all_entities[formatted_ent_id],
                )
                mention_store[doc][formatted_span] = new_mention

    with open(output, "wb+") as handle:  # type: ignore
        pickle.dump(mention_store, handle)  # type: ignore


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--edl-output", help="Path to EDL dir containing output", type=Path)
    p.add_argument("--output", help="Path to output file", type=Path)
    args = p.parse_args()
    main(args.edl_output, args.output)