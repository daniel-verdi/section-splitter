# Scientific Paper Rhetorical Section Classifier

Code and annotation resources for classifying sections of scientific papers into
rhetorical roles such as Introduction, Methods, Results, Discussion, and
Conclusion.

Authors: Daniel Verdi, Jacob Aarup Dalsgaard, Roberta Sinatra

## Overview

This repository supports a reproducible workflow for extracting section headers
from S2ORC papers, assigning rule-based rhetorical section labels, preparing
optional LLM annotation batches, collecting optional human annotations, and
evaluating label quality.

The main classifier is implemented as a standalone Polars pipeline. The
repository also includes scripts for downloading and preparing S2ORC data,
stored annotation materials, a Prolific-oriented annotation interface, and
evaluation notebooks used during analysis.

## Associated Paper

TODO: add paper title, venue, DOI, and/or preprint link.

- *TODO: add paper title*
  Daniel Verdi, Jacob Aarup Dalsgaard, Roberta Sinatra
  TODO: add DOI/arXiv/preprint link

## Data Release

You can find the labeled data here: https://doi.org/10.5281/zenodo.20814302

This project uses [S2ORC: The Semantic Scholar Open Research Corpus](https://github.com/allenai/s2orc).
Raw S2ORC files are downloaded from Semantic Scholar and are not redistributed
in this repository. Generated Parquet outputs and large classifier outputs are
created locally during execution.

## What Is Included In The Repository

Pipeline scripts:

- [`section_classifier.py`](section_classifier.py)
  Main Polars pipeline for extracting S2ORC section headers, assigning
  rule-based rhetorical labels, aggregating section text, and filtering papers
  by quality heuristics.
- [`scripts/s2orc/download_dataset.py`](scripts/s2orc/download_dataset.py)
  Downloads the latest Semantic Scholar dataset release files for S2ORC or
  another dataset name.
- [`scripts/s2orc/process_s2orc.py`](scripts/s2orc/process_s2orc.py)
  Converts raw S2ORC JSONL parts into partitioned Parquet with decoded
  annotation spans.

Annotation and evaluation materials:

- [`llm_annotations/`](llm_annotations)
  Utilities and stored inputs/outputs for optional OpenAI Batch API labeling of
  sampled section rows.
- [`prolific_annotations/`](prolific_annotations)
  Human annotation data and a PHP/MySQL annotation interface. See
  [`prolific_annotations/interface/README.md`](prolific_annotations/interface/README.md)
  for deployment details.
- [`evaluations/`](evaluations)
  Notebooks for inspecting samples and evaluating classifier, LLM, or human
  annotation outputs.

Environment and documentation files:

- [`requirements.txt`](requirements.txt)
  Python dependencies for the scripts and notebooks.
- [`README.md`](README.md)
  Repository overview and reproduction instructions.

## What Is Not Included

Some inputs and outputs are expected to be generated locally or obtained from
external services:

- raw S2ORC downloads such as `s2orc/s2orc_part1.zip`;
- converted S2ORC Parquet outputs such as `s2orc.parquet/`;
- classifier outputs such as `classifier_output/`;
- local Python environments and caches;
- local credentials, API keys, and database passwords.

If your local file layout differs, use the command-line arguments documented
below to point the scripts at your local paths.

## Environment Setup

Use Python 3.10+ if possible, then install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If you prefer `uv`, create and use an environment with:

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## API Authentication

Some workflows require credentials:

- `S2_API_KEY` for the Semantic Scholar datasets API.
- `OPENAI_API_KEY` for the optional LLM batch annotation scripts.
- MySQL/PHP configuration for the optional Prolific annotation interface.

Set the Semantic Scholar key before downloading S2ORC:

```bash
export S2_API_KEY="your-api-key"
```

Set the OpenAI key before running scripts under `llm_annotations/`:

```bash
export OPENAI_API_KEY="your-api-key"
```

The Prolific annotation interface stores database credentials in its PHP and
helper-script configuration files; see
[`prolific_annotations/interface/README.md`](prolific_annotations/interface/README.md).

## Running The Pipeline

The core pipeline has three steps:

1. download S2ORC;
2. convert raw S2ORC JSONL parts to Parquet;
3. classify sections in each generated Parquet part.

### 1. Download S2ORC

Download the latest S2ORC release:

```bash
python scripts/s2orc/download_dataset.py --dataset s2orc --output-dir s2orc
```

This creates files like `s2orc/s2orc_part1.zip`, `s2orc/s2orc_part2.zip`, and
so on.

### 2. Convert Raw S2ORC To Parquet

Decode the raw S2ORC annotation fields and write partitioned Parquet:

```bash
python scripts/s2orc/process_s2orc.py \
  --input-glob "s2orc/s2orc_part*.zip" \
  --schema-sample "s2orc/s2orc_part1.zip" \
  --output s2orc.parquet
```

The defaults match the command above, so `python scripts/s2orc/process_s2orc.py`
is enough when the downloaded files are in `s2orc/`. If Polars runs out of
memory during conversion, see [Reproducibility Notes](#reproducibility-notes).

### 3. Classify Sections

Run the rule-based section classifier on the Parquet output from step 2. The
classifier can read a folder of Parquet files directly:

```bash
python section_classifier.py \
  --input s2orc.parquet \
  --output_dir classifier_output
```

This treats the whole folder as one Polars scan and writes one set of output
files named after the input folder. For large runs, processing one Parquet file
at a time is often easier to monitor and less risky for memory usage:

```bash
python section_classifier.py \
  --input s2orc.parquet/00000000.parquet \
  --output_dir classifier_output
```

To process every generated part separately, loop over the Parquet files:

```bash
for input_file in s2orc.parquet/*.parquet; do
  python section_classifier.py \
    --input "$input_file" \
    --output_dir classifier_output
done
```

For quick testing, limit rows:

```bash
python section_classifier.py \
  --input s2orc.parquet/00000000.parquet \
  --output_dir classifier_output_test \
  --rows 1000
```

The classifier writes three output datasets under the output directory:

- `classified.parquet/`: one row per detected section header.
- `aggregated.parquet/`: section text aggregated by paper and label.
- `filtered.parquet/`: final filtered sections used for downstream analysis.

### 4. Generate Annotation Samples

Generate deterministic samples from `classified.parquet` for downstream LLM and
human annotation. The sampler hashes `corpusid`, so the same inputs, seed, and
sampling rates produce the same paper samples.

```bash
python evaluations/create_samples.py \
  --classified-dir classifier_output/classified.parquet \
  --output-dir samples
```

This writes:

- `samples/auto_eval_sample.parquet`: larger sample for LLM batch annotation.
- `samples/manual_eval_sample.parquet`: filtered human annotation sample.
- `samples/manual_eval_sample.csv`: CSV version for the human annotation
  workflow.

The defaults use hash seed `33`, an LLM sampling modulus of `10000`, and a human
sampling modulus of `100000`. To also write the human CSV directly into the
Prolific annotation folder, pass an extra output path:

```bash
python evaluations/create_samples.py \
  --classified-dir classifier_output/classified.parquet \
  --output-dir samples \
  --manual-csv-output prolific_annotations/sample_100.csv
```

## Evaluation And Annotation Workflows

### Optional LLM Annotation

The `llm_annotations/` workflow prepares sampled rows for the OpenAI Batch API:

```bash
python llm_annotations/create_batches.py \
  --input-file samples/auto_eval_sample.parquet \
  --batch-output-dir llm_annotations/batch_input \
  --results-output-dir llm_annotations/output
```

Then submit the generated batch files:

```bash
cd llm_annotations
python call_api.py
```

`create_batches.py` writes JSONL requests to `batch_input/`. `call_api.py`
submits those files and stores timestamped results in `output/`.

### Optional Prolific Annotation

The `prolific_annotations/interface/` folder contains a PHP/MySQL annotation
tool for human labels. Follow
[`prolific_annotations/interface/README.md`](prolific_annotations/interface/README.md)
to create the database, import paper sections, configure credentials, and export
annotations.

Use `samples/manual_eval_sample.csv` as the input CSV for the human annotation
interface. The interface README includes a local smoke-test flow using the
included sample data.

### Optional Evaluation

Use the notebooks in `evaluations/` to inspect samples and evaluate classifier,
LLM, or human annotation outputs:

- [`evaluations/sample.ipynb`](evaluations/sample.ipynb)
- [`evaluations/run_evaluations.ipynb`](evaluations/run_evaluations.ipynb)

## Classification Labels

The classifier uses these main rhetorical labels:

- **Introduction:** Sets the stage, introduces the topic, explains motivation,
  states the core problem or research questions, and provides a structural
  overview.
- **Literature Review:** Discusses previous work and state-of-the-art. Also
  serves as the main body for review papers without new findings.
- **Methods:** Details how the research was conducted, including study design,
  data, algorithms, and experimental setups.
- **Development:** Core argumentative or theoretical sections that are not
  empirical, common in fields such as philosophy, theoretical math, or law.
- **Results:** Presentation of findings, data, and primary observations.
- **Discussion:** Interpretation of results, broader implications, and
  limitations.
- **Conclusion:** Summary, closing remarks, and future work.

The code also uses helper labels such as `ending`, `other`, and `figure_table`
to identify non-core sections during filtering.

## Reproducibility Notes

- Script defaults assume raw S2ORC files are in `s2orc/`, converted Parquet is
  written to `s2orc.parquet/`, and classifier outputs are written under
  `classifier_output/`.
- The S2ORC conversion and classification steps are data intensive. For testing,
  use `--rows` with `section_classifier.py` before running the full dataset.
- If Polars runs out of memory on large parts, reduce its streaming work size.
  Depending on the Polars version, one of these environment variables may apply:

```bash
export POLARS_IDEAL_MORSEL_SIZE=10000
export POLARS_STREAMING_CHUNK_SIZE=10000
```

Start with one variable at a time if you know which Polars version you are
using; setting both is a pragmatic fallback when reproducing the pipeline across
different environments.

## Citation

If you use this repository, please cite the associated paper.

```bibtex
@article{TODO,
  title = {TODO: add paper title},
  author = {Verdi, Daniel and Dalsgaard, Jacob Aarup and Sinatra, Roberta},
  year = {TODO},
  doi = {TODO}
}
```

Upstream data resources should also be cited where appropriate, especially
S2ORC and Semantic Scholar.

## License

TODO: add repository license information.

## Contact

TODO: add contact details or preferred issue-reporting route.
