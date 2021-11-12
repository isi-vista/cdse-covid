"""
Takes the claim data and uses AMR graphs to extract claimers and x-variables.

You will need to run this in your transition-amr virtual environment.
"""
import argparse
import logging
from os import chdir, getcwd, makedirs
from pathlib import Path
from typing import List
import uuid
import spacy


from transition_amr_parser.parse import AMRParser  # pylint: disable=import-error

from amr_utils.amr_readers import AMR_Reader, Metadata_Parser

from cdse_covid.claim_detection.run_claim_detection import ClaimDataset
from cdse_covid.pegasus_pipeline.run_amr_parsing_all import refine_sentence, tokenize_sentence
from cdse_covid.semantic_extraction.models import AMRLabel
from cdse_covid.semantic_extraction.utils.claimer_utils import identify_claimer
from cdse_covid.semantic_extraction.utils.amr_extraction_utils import identify_x_variable_covid, identify_x_variable

COVID_DOMAIN = "covid"


def main(input_dir, output, *, max_tokens: int, spacy_model, parser_path, domain):

    cdse_path = getcwd()

    # We assume that the checkpoint is in this location within the repo
    in_checkpoint = f"{parser_path}/DATA/AMR2.0/models" \
                    "/exp_cofill_o8.3_act-states_RoBERTa-large-top24" \
                    "/_act-pos-grh_vmask1_shiftpos1_ptr-lay6-h1_grh-lay123-h2-allprev" \
                    "_1in1out_cam-layall-h2-abuf/ep120-seed42/checkpoint_best.pt"

    if not Path(in_checkpoint).exists():
        raise RuntimeError(f"Could not find checkpoint file {in_checkpoint}!")
    if not input_dir.exists():
        raise RuntimeError(f"Input directory {args.input} could not be found!")
    if not Path(output).exists():
        makedirs(output)

    chdir(parser_path)
    amr_parser = AMRParser.from_checkpoint(in_checkpoint)
    chdir(cdse_path)

    claim_ds = ClaimDataset.load_from_dir(input_dir)

    for claim in claim_ds.claims:
        tokenized_sentence = tokenize_sentence(
            claim.claim_sentence, spacy_model.tokenizer, max_tokens
        )
        annotations = amr_parser.parse_sentences([tokenized_sentence])
        metadata, graph_metadata = Metadata_Parser().readlines(annotations[0][0])
        amr, alignments = AMR_Reader._parse_amr_from_metadata(metadata["tok"], graph_metadata)
        tokenized_claim = tokenize_sentence(
            claim.claim_text, spacy_model.tokenizer, max_tokens
        )
        possible_claimer = identify_claimer(tokenized_claim, amr, alignments)
        if possible_claimer:
            claim.claimer = possible_claimer

        claim_annotations = amr_parser.parse_sentences([tokenized_claim])
        claim_metadata, claim_graph_metadata = Metadata_Parser().readlines(
            claim_annotations[0][0]
        )
        claimr, claim_alignments = AMR_Reader._parse_amr_from_metadata(
            claim_metadata["tok"], claim_graph_metadata
        )
        if domain == COVID_DOMAIN:
            possible_x_variable = identify_x_variable_covid(
                claimr, claim_alignments, claim.claim_template
            )
        else:
            claim_ents = {
                ent.text: ent.label_ for ent in spacy_model(claim.claim_text).ents
            }
            claim_pos = {
                token.text: token.pos_ for token in spacy_model(claim.claim_text).doc
            }
            possible_x_variable = identify_x_variable(
                claimr, claim_alignments, claim_ents, claim_pos
            )
        if possible_x_variable:
            claim.x_variable = possible_x_variable

        amr_label = AMRLabel(int(uuid.uuid1()), amr, alignments)
        claim.add_theory("amr", amr_label)

    claim_ds.save_to_dir(output)

    logging.info("AMR output saved to %s", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Input docs", type=Path)
    parser.add_argument("--output", help="AMR output dir", type=Path)
    parser.add_argument("--amr-parser-model", type=Path)
    parser.add_argument(
        "--max-tokens",
        help="Max tokens allowed in a sentence to be parsed",
        type=int,
        default=50
    )
    parser.add_argument(
        "--domain", help="`covid` or `general`", type=str, default="general"
    )

    args = parser.parse_args()

    model = spacy.load("en_core_web_sm")

    main(
        args.input,
        args.output,
        max_tokens=args.max_tokens,
        spacy_model=model,
        parser_path=args.amr_parser_model,
        domain=args.domain
    )
