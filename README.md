# Claim Detection & Semantics Extraction (Covid-19)

## Installation

1. Clone repo
2. Create Python virtual environment
   - e.g. `conda create -n covid-claims python=3.8`
3. Make sure that your current Java environment is **Java 8**.
   - If the setup fails at the JAMR step, check that Java 8 is configured
      for the newly downloaded `transition-amr-parser` project.
   - e.g. `spack load openjdk@1.8.0_202-b08`
4. Make sure `cuda` is enabled if you are on a machine with a GPU.
   - e.g. 'spack load cuda@10.0.130; spack load cudnn@7.6.5.32-10.2'
5. Run `make install [$isi_username]`
   - This assumes that your conda installation is within `~/miniconda3`. If it is not, replace Line 27 of `setup.sh` with: `source ~/PATH_TO_MINICONDA_INSTALL`.
   - If you provide `isi_username`, it will assume that you can access the `minlp-dev-01` server and that you are working from a local system.
      In that case, you will be prompted for a password after you see
      `"Downloading model..."`
      If not, it will assume that you are working from a `/nas`-mounted server.
6. You will also need to download and unzip this file into `data/`:
   1. UIUC EDL data (param: `edl.edl_output_dir`): https://drive.google.com/file/d/16ANEPjqy4byNY3B2BmYqsu1ZcBlp9tfR/view?usp=sharing
   2. Change the edl_output_file edl param. 

## Docker
These instructions assume that you are building the image on the SAGA cluster.
1. Clone repo
2. `cd` into `cdse-covid` and clone the following repos:
   1. `git clone https://github.com/isi-vista/aida-tools.git`
   2. `git clone https://github.com/elizlee/amr-utils.git`
   3. `git clone https://github.com/isi-vista/saga-tools.git`
   4. `git clone https://github.com/IBM/transition-amr-parser.git`
      1. Make sure that your `transition-amr-parser` installation is updated and on the `master` branch.
      2. `cd` to `transition-amr-parser/preprocess` and do the following:
         1. `git clone https://github.com/jflanigan/jamr.git`
         2. `git clone https://github.com/damghani/AMR_Aligner.git`
         3. `mv AMR_Aligner kevin`
         4. `cd transition-amr-parser/preprocess/kevin`:
            1. `git clone https://github.com/moses-smt/mgiza.git`
   5. Copy the following files from `/scratch/dockermount/cdse_covid_resources`:
      1. The Wikidata classifier: `wikidata_classifier.state_dict` --> `cdse-covid/wikidata_linker/resources`
      2. The AMR parser model: `/scratch/dockermount/cdse_covid_resources/AMR2.0` --> `transition-amr-parser/DATA`
   6. `cd` back into `cdse-covid` and run
      ```
      docker build . -t isi-cdse-covid:<tag>
      ```

## Usage

### Via Pegasus WFMS

1. Generate workflow
```
conda activate <cdse-covid-env>
python -m cdse_covid.pegasus_pipeline.claim_pipeline params/claims_pipeline.params
```
2. Navigate to experiment dir specified in your params file, execute the workflow, and monitor the progress
```
bash setup.sh
pegasus-status PEGASUS/RUN/DIR -w 60
```

### Via Shell Script
We provide a simple way to run the whole pipeline without needing Pegasus WMS.
1. Create a parameter file with your own values for the parameters in
   `params/run_pipeline_params.params`
2. Make sure that your cdse-covid conda environment is active.
3. Run
   ```
   bash ./run_pipeline.sh your/params/file
   ```

### Via Individual Scripts

1. Create the AMR files
   
   The files in `TXT_FILES` should consist of sentences separated by line.
   ```
   conda activate transition-amr-parser
   python -m cdse_covid.pegasus_pipeline.run_amr_parsing_all \
       --corpus TXT_FILES \
       --output AMR_FILES \
       --max-tokens MAX_TOKENS \
       --amr-parser-model TRANSITION_AMR_PARSER_PATH
   ```
2. Preprocessing
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.pegasus_pipeline.ingesters.aida_txt_ingester \
       --corpus TXT_FILES --output SPACIFIED --spacy-model SPACY_PATH
   ```
3. EDL ingestion
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.pegasus_pipeline.ingesters.edl_output_ingester \
       --edl-output EDL_OUTPUT --output EDL_MAPPING_FILE
   ```
4. Claim detection
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.claim_detection.run_claim_detection \
       --input SPACIFIED \
       --patterns claim_detection/topics.json \
       --out CLAIMS_OUT \
       --spacy-model SPACY_PATH
   ```
5. Semantic extraction from AMR
   ```
   conda activate transition-amr-parser
   python -m cdse_covid.semantic_extraction.run_amr_parsing \
       --input CLAIMS_OUT \
       --output AMR_CLAIMS_OUT \
       --amr-parser-model TRANSITION_AMR_PARSER_PATH \
       --max-tokens MAX_TOKENS \
       --domain DOMAIN
   ```
6. Semantic extraction from SRL
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.semantic_extraction.run_srl \
       --input AMR_CLAIMS_OUT \
       --output SRL_OUT \
       --spacy-model SPACY_PATH
   ```
7. Wikidata linking
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.semantic_extraction.run_wikidata_linking \
       --claim-input CLAIMS_OUT \
       --srl-input SRL_OUT \
       --amr-input AMR_CLAIMS_OUT \
       --output WIKIDATA_OUT
   ```
8. Entity merging
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.semantic_extraction.run_entity_merging \
       --edl EDL_MAPPING_FILE \
       --qnode-freebase QNODE_FREEBASE_MAPPING \
       --freebase-to-qnodes FREEBASE_TO_QNODES \
       --claims WIKIDATA_OUT \
       --output ENTITY_OUT \
       --include-contains
   ```
9. Postprocessing
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.pegasus_pipeline.convert_claims_to_json \
       --input ENTITY_OUT \
       --output OUTPUT_FILE
   ``` 
10. Converting the JSON to AIF
   ```
   conda activate <cdse-covid-env>
   python -m cdse_covid.pegasus_pipeline.ingesters.claims_json_to_aif \
      --claims-json OUTPUT FILE \
      --aif-dir AIF_OUTPUT_DIR
   ```

## Contributing

1. Before pushing, first run `make precommit` to run all precommit checks.
   - You can run these checks individually if you so desire. Please see (./Makefile)[Makefile] for a list of all commands.
2. After ensuring all linting requirements are met, rebase the new branch against master.
3. Create a new PR, requesting review from at least one collaborator.
