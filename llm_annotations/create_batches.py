# Prepare Batch Files
# The Batch API is ~50% cheaper than real-time requests and has higher rate limits.
# The tradeoff is async execution with up to 24h completion window.
# OpenAI enforces a 2M enqueued-token limit across all in-progress batches in the org.
# We split requests into multiple files so each file stays safely under that ceiling.
# Files are submitted one at a time (or you can wait for one to finish before submitting the next).

# Setup and configurations

import argparse
import json
from pathlib import Path
import pandas as pd
import tiktoken
from dotenv import load_dotenv

load_dotenv()
PAPER_ID_COL     = 'corpusid'
HEADER_COL       = 'extracted'
CONTENT_COL      = 'section_text'

# --- MODEL PARAMETERS (static per request) ---
MODEL_PARAMETERS = {
    "text": {
        "format": {
            "type": "json_schema",
            "name": "labeled_confidence_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Chosen section label"},
                    "confidence": {
                        "type": "string",
                        "description": "Confidence in the classification (high, medium, or low)",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["label", "confidence"],
                "additionalProperties": False
            }
        },
        "verbosity": "medium"
    },
    "reasoning": {"effort": "low"},
    "tools": [],
    "store": True
}

# --- PROMPT ---
PROMPT_TEMPLATE = """
# TASK
Analyze the CURRENT_CONTENT below. Use the content snippet and the context from the previous and following headers to assign the most accurate section label. The snippet contains the first 300 words of the text.

# SECTION DEFINITIONS
- `introduction`: Introduces the topic, problem, research questions, motivation, and/or paper structure.
- `lit_review`: Discusses previous work and the state-of-the-art. It is also the main body of papers that only review existing literature without presenting new findings.
- `methods`: How the research was done (e.g., experiments, data, algorithms).
- `results`: Presents findings and data without interpretation.
- `discussion`: Interprets the results, discusses implications, and limitations.
- `conclusion`: Summarizes the paper and often discusses future work.
- `case_report`: In Medicine papers, a narrative of a patient case or group of related cases. Often includes patient profiles, unique events, or specific interventions/treatments and their outcomes.
- `development`: The core argumentative or theoretical advancement of a paper that isn't presenting empirical methods or results. Common in fields like philosophy, theoretical math, or law. Only use it if the other labels really don't apply.
- `something_else`: Other administrative sections that do not fit in any of the other labels. Avoid using it whenever possible.
- `ambiguous`: Use this label only as a *last resort* if it's impossible to determine the section's purpose from the given text and context.

# IMPORTANT NOTES
- A single logical section (like 'Methods') might be broken into several smaller headers (e.g., '3.1 Study Design', then '3.2 Participants'). Your job is to label *each* of these individual headers with the parent label, which would be `methods` in this case. 
- Not all papers have all sections! Most will only have a subset. A computer science paper might not have a separate `lit_review`, and a philosophy paper won't have experimental `results`. Your task is to label what's there, not what "should" be there.
- Always choose a category from the SECTION DEFINITIONS, never invent a new label.

# RESPONSE
Provide your response in a JSON format with these keys:
1. "label": Your chosen section label (string).
2. "confidence": Your confidence in this classification (string: "high", "medium", or "low").

---

# EXAMPLE
## CONTEXT
  - PREVIOUS_HEADERS:
    "- 1. Introduction
     - 2. Related Work
     - 2.1. Neural Network Pruning
     - 2.2. Quantization Aware Training
     - 3. Our Proposed Method"

==> CURRENT ROW IS HERE
## CURRENT_CONTENT
    "3.1. Dataset
We use the publicly available ImageNet (ILSVRC 2012) dataset, which consists of over 1.2 million training images from 1,000 classes. The images vary in resolution and are resized to 224x224 pixels during preprocessing."

  - FOLLOWING_HEADERS:
"      - 3.2. Model Architecture
     - 3.3. Training Procedure
     - 4. Experiments and Results
     - 4.1. Main Findings
     - 4.2. Ablation Studies"

**Response:**
{{
  "label": "methods",
  "confidence": "high"
}}

---
# YOUR TURN
## CONTEXT
  - PREVIOUS_HEADERS:
{previous_headers_list}

==> CURRENT ROW IS HERE
- CURRENT_CONTENT:
{section_content_snippet}

  - FOLLOWING_HEADERS:
{following_headers_list}

*Response:*
"""

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create OpenAI Batch API JSONL files from an annotation sample."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("auto_eval_sample.parquet"),
        help="Parquet sample to convert into batch requests.",
    )
    parser.add_argument(
        "--batch-output-dir",
        type=Path,
        default=Path("batch_input"),
        help="Directory where batch_input_N.jsonl files are written.",
    )
    parser.add_argument(
        "--results-output-dir",
        type=Path,
        default=Path("output"),
        help="Directory reserved for Batch API outputs.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="OpenAI model name to include in each request body.",
    )
    parser.add_argument(
        "--token-limit",
        type=int,
        default=300,
        help="Maximum content snippet length in tokens.",
    )
    parser.add_argument(
        "--batch-token-limit",
        type=int,
        default=1_800_000,
        help="Maximum estimated prompt tokens per JSONL batch file.",
    )
    return parser.parse_args()


def write_batch_file(requests_list: list, file_counter: int, base_name: Path) -> str:
    """Write a list of request dicts to a numbered JSONL file. Returns the filename."""
    filename = base_name.parent / f"{base_name.name}_{file_counter}.jsonl"
    with filename.open("w") as f:
        for req in requests_list:
            f.write(json.dumps(req) + "\n")
    print(f"  ✅ {filename}  ({len(requests_list)} requests)")
    return str(filename)


def main() -> None:
    """Prepare/create the batch input files."""
    args = parse_args()
    args.batch_output_dir.mkdir(parents=True, exist_ok=True)
    args.results_output_dir.mkdir(parents=True, exist_ok=True)
    batch_output_base = args.batch_output_dir / "batch_input"

    print("✅ Configuration done.")

    try:
        encoding = tiktoken.get_encoding("o200k_base")
    except Exception as e:
        print(f"Error getting tokenizer: {e}")
        exit()

    # Load and filter data
    df = pd.read_parquet(args.input_file)
    print(f"✅ Loaded {len(df)} rows from {args.input_file}.")

    # Remove irrelevant sections - we don't need the LLM to label those, it would just waste tokens and budget
    df = df[
        (df[CONTENT_COL].str.strip() != "") &
        (~df['sec_label_extended'].isin(['figure_table', 'ending', 'other']))
    ]
    print(f"   After filtering: {len(df)} rows.")

    all_input_data    = []   # for mapping results back to originals
    batch_filenames   = []   # list of written JSONL paths

    file_counter          = 1
    current_batch_reqs    = []
    current_batch_tokens  = 0
    total_requests        = 0

    print("\nPreparing batch files...")
    for paper_id, group in df.groupby(PAPER_ID_COL):
        group = group.reset_index(drop=True)

        for index, row in group.iterrows():
            # Build header context windows
            prev_headers = group.iloc[max(0, index - 5):index][HEADER_COL].tolist()
            next_headers = group.iloc[index + 1:min(len(group), index + 6)][HEADER_COL].tolist()
            prev_str = "\n".join(f" - {h} " for h in prev_headers)
            next_str = "\n".join(f" - {h} " for h in next_headers)

            # Truncate content snippet
            full_content = str(row[CONTENT_COL])
            tokens = encoding.encode(full_content)
            snippet = encoding.decode(tokens[:args.token_limit]) if len(tokens) > args.token_limit else full_content

            # Format prompt
            prompt = PROMPT_TEMPLATE.format(
                previous_headers_list=prev_str,
                section_content_snippet=snippet,
                following_headers_list=next_str
            )
            prompt_tokens = len(encoding.encode(prompt))

            # Split into a new file if we'd exceed the token limit
            if current_batch_reqs and (current_batch_tokens + prompt_tokens > args.batch_token_limit):
                batch_filenames.append(
                    write_batch_file(current_batch_reqs, file_counter, batch_output_base)
                )
                file_counter += 1
                current_batch_reqs   = []
                current_batch_tokens = 0

            custom_id = f"{paper_id}-{index}"

            request_data = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": args.model,
                    "input": [{
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }],
                    **MODEL_PARAMETERS
                }
            }

            current_batch_reqs.append(request_data)
            current_batch_tokens += prompt_tokens
            total_requests += 1
            all_input_data.append({"custom_id": custom_id, "original_header": row[HEADER_COL]})

    # Write last batch
    if current_batch_reqs:
        batch_filenames.append(
            write_batch_file(current_batch_reqs, file_counter, batch_output_base)
        )

    print(f"\n✅ Done. {total_requests} total requests across {len(batch_filenames)} batch file(s).")


if __name__ == "__main__":
    main()
