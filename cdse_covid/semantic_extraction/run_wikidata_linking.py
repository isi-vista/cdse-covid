"""Run WikiData over claim semantics."""
import argparse
import logging
from pathlib import Path
from typing import Any, List, Sequence

from cdse_covid.claim_detection.run_claim_detection import ClaimDataset
from cdse_covid.semantic_extraction.entities import WikidataQnode
from wikidata_linker.wikidata_linking import disambiguate_kgtk


def _find_links(span: str, tokens: Sequence[str]) -> Any:
    """Find WikiData links for a set of tokens."""
    return (disambiguate_kgtk(span, token, k=1) for token in tokens)


def main(claim_input: Path, srl_input: Path, amr_input: Path, output: Path) -> None:
    """Entry point to linking script."""
    ds1 = ClaimDataset.load_from_dir(claim_input)
    ds2 = ClaimDataset.load_from_dir(srl_input)
    ds3 = ClaimDataset.load_from_dir(amr_input)
    claim_dataset = ClaimDataset.from_multiple_claims_ds(ds1, ds2, ds3)

    for claim in claim_dataset:
        if claim.claimer:
            claimer_links = _find_links(claim.claim_sentence, [claim.claimer.text])
            top_link = create_wikidata_qnodes(claimer_links)
            if top_link:
                claim.claimer_qnode = top_link[0]
        if claim.x_variable:
            srl_links = _find_links(claim.claim_sentence, [claim.x_variable.text])
            top_link = create_wikidata_qnodes(srl_links)
            if top_link:
                claim.x_variable_qnode = top_link[0]

    claim_dataset.save_to_dir(output)

    logging.info("Saved claims with Wikidata to %s", output)


def create_wikidata_qnodes(links: List[Any]) -> List[WikidataQnode]:
    """Create WikiData Qnodes from links."""
    all_qnodes = []
    for link in links:
        if not link["options"]:
            continue
        qnode = WikidataQnode(
            link["options"][0]["qnode"],
            link["options"][0]["rawName"],
            link["options"][0]["definition"],
            link["query"],
        )
        all_qnodes.append(qnode)
    return all_qnodes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-input", type=Path)
    parser.add_argument("--srl-input", type=Path)
    parser.add_argument("--amr-input", type=Path)
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()

    main(
        args.claim_input,
        args.srl_input,
        args.amr_input,
        args.output,
    )
