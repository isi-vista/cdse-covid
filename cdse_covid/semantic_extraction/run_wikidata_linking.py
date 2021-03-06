"""Run WikiData over claim semantics."""
import argparse
import logging
from pathlib import Path

from nltk.stem import WordNetLemmatizer
import spacy
from spacy.language import Language
import torch

from cdse_covid.claim_detection.run_claim_detection import ClaimDataset
from wikidata_linker.get_claim_semantics import get_best_qnode_for_mention_text
from wikidata_linker.linker import WikidataLinkingClassifier
from wikidata_linker.qnode_mapping_utils import load_tables
from wikidata_linker.wikidata_linking import CPU


def main(
    claim_input: Path,
    state_dict: Path,
    output: Path,
    spacy_model: Language,
    max_batch_size: int = 8,
    device: str = CPU,
) -> None:
    """Entry point to linking script."""
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    claim_dataset = ClaimDataset.load_from_key_value_store(claim_input)

    linking_model = WikidataLinkingClassifier()
    model_ckpt = torch.load(state_dict, map_location=torch.device(device))
    linking_model.load_state_dict(model_ckpt, strict=False)
    linking_model.to(device)

    qnode_tables = load_tables()

    lemmatizer = WordNetLemmatizer()

    for claim in claim_dataset:
        claim_amr = claim.get_theory("amr")
        claim_alignments = claim.get_theory("alignments")
        if claim_amr and claim_alignments:
            if claim.x_variable:
                best_qnode = get_best_qnode_for_mention_text(
                    claim.x_variable,
                    claim,
                    claim_amr,
                    claim_alignments,
                    spacy_model,
                    linking_model,
                    lemmatizer,
                    qnode_tables,
                    max_batch_size,
                    device,
                )
                if best_qnode:
                    claim.x_variable_type_qnode = best_qnode
        else:
            logger.warning(
                "Could not load AMR or alignments for claim sentence '%s'", claim.claim_sentence
            )

    claim_dataset.save_to_key_value_store(output)

    logger.info("Saved claims with Wikidata to %s", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-input", type=Path)
    parser.add_argument("--state-dict", type=Path, help="Path to `wikidata_classifier.state_dict`")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--max-batch-size", help="Max batch size; 8 is recommended", type=int, default="8"
    )
    parser.add_argument("--device", type=str, default="cpu")

    args = parser.parse_args()

    model = spacy.load("en_core_web_md")

    main(args.claim_input, args.state_dict, args.output, model, args.max_batch_size, args.device)
