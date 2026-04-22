"""Create deterministic samples for LLM and human annotation.

The classifier writes one row per detected section under
``classifier_output/classified.parquet``. This script deterministically samples
papers from that dataset by hashing ``corpusid`` so the same inputs and seed
produce the same annotation samples.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


EXCLUDED_HUMAN_LABELS = {"figure_table", "ending", "other"}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate deterministic LLM and human annotation samples."
    )
    parser.add_argument(
        "--classified-dir",
        type=Path,
        default=Path("classifier_output/classified.parquet"),
        help="Classifier output classified.parquet directory or file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
        help="Directory where sample files will be written.",
    )
    parser.add_argument(
        "--hash-seed",
        type=int,
        default=33,
        help="Seed for deterministic corpusid hashing.",
    )
    parser.add_argument(
        "--auto-modulus",
        type=int,
        default=10_000,
        help="Keep papers where hash(corpusid) modulo this value is 0 for the LLM sample.",
    )
    parser.add_argument(
        "--manual-modulus",
        type=int,
        default=100_000,
        help="Keep papers where hash(corpusid) modulo this value is 0 for the human sample.",
    )
    parser.add_argument(
        "--manual-csv-output",
        type=Path,
        default=None,
        help="Optional extra CSV path for the filtered human annotation sample.",
    )
    return parser.parse_args()


def sampled_papers(lf: pl.LazyFrame, *, hash_seed: int, modulus: int) -> pl.LazyFrame:
    """Filter a LazyFrame to a deterministic corpusid hash sample."""
    return lf.filter(pl.col("corpusid").hash(seed=hash_seed) % modulus == 0)


def filtered_human_sample(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Remove rows that should not be sent to human annotators."""
    return lf.filter(
        (pl.col("section_text").str.strip_chars() != "")
        & (~pl.col("sec_label_extended").is_in(EXCLUDED_HUMAN_LABELS))
    )


def main() -> None:
    """Create Parquet and CSV sample artifacts."""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning classified sections from: {args.classified_dir}")
    lf = pl.scan_parquet(args.classified_dir)

    auto_sample = sampled_papers(
        lf,
        hash_seed=args.hash_seed,
        modulus=args.auto_modulus,
    )
    manual_sample = sampled_papers(
        lf,
        hash_seed=args.hash_seed,
        modulus=args.manual_modulus,
    )
    manual_filtered = filtered_human_sample(manual_sample)

    auto_path = args.output_dir / "auto_eval_sample.parquet"
    manual_parquet_path = args.output_dir / "manual_eval_sample.parquet"
    manual_csv_path = args.output_dir / "manual_eval_sample.csv"

    print(f"Writing LLM sample to: {auto_path}")
    auto_sample.sink_parquet(auto_path)

    print(f"Writing human sample Parquet to: {manual_parquet_path}")
    manual_filtered.sink_parquet(manual_parquet_path)

    print(f"Writing human sample CSV to: {manual_csv_path}")
    manual_filtered.collect().write_csv(manual_csv_path)

    if args.manual_csv_output:
        args.manual_csv_output.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing extra human sample CSV to: {args.manual_csv_output}")
        manual_filtered.collect().write_csv(args.manual_csv_output)

    print("Sampling complete.")


if __name__ == "__main__":
    main()
