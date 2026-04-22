"""Convert raw S2ORC JSONL parts into partitioned Parquet files.

S2ORC full-text files include nested annotation fields encoded as JSON strings.
This script decodes the annotation columns that the section classifier needs,
keeps the paper text and identifiers, and writes partitioned Parquet output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


DEFAULT_INPUT_GLOB = "s2orc/s2orc_part*.zip"
DEFAULT_SCHEMA_SAMPLE = "s2orc/s2orc_part1.zip"
DEFAULT_OUTPUT_PATH = "s2orc.parquet"
DEFAULT_PARTITION_SIZE = 1_000_000


START_END_STRUCT = pl.Struct({"end": pl.UInt32, "start": pl.UInt32})
REF_ID_STRUCT = pl.Struct({"ref_id": pl.String})
ID_TYPE_STRUCT = pl.Struct({"id": pl.String, "type": pl.String})
ID_ONLY_STRUCT = pl.Struct({"id": pl.String})
BIBENTRY_ATTR_STRUCT = pl.Struct(
    {"id": pl.String, "matched_paper_id": pl.String, "doi": pl.String}
)
SECTION_ATTR_STRUCT = pl.Struct({"n": pl.String})


def infer_schema(schema_sample: str | Path) -> pl.Schema:
    """Infer a stable schema from one raw S2ORC part."""
    return pl.scan_ndjson(str(schema_sample), infer_schema_length=None).collect_schema()


def decode_annotations(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Decode S2ORC annotation JSON strings into typed Polars list/struct columns."""
    # The annotation payloads are strings containing arrays of start/end spans.
    # Explicit schemas keep Polars from inferring incompatible types across parts.
    return (
        lf.with_columns(pl.col("annotations").struct.unnest())
        .select(pl.exclude("annotations"))
        .with_columns(
            [
                pl.col("abstract").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("author").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("authoraffiliation").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("authorfirstname").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("authorlastname").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("bibauthor").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("bibauthorfirstname").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("bibauthorlastname").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("bibentry").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "attributes": BIBENTRY_ATTR_STRUCT,
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                            }
                        )
                    )
                ),
                pl.col("bibref").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                                "attributes": REF_ID_STRUCT,
                            }
                        )
                    )
                ),
                pl.col("bibtitle").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("bibvenue").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("figure").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "attributes": ID_TYPE_STRUCT,
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                            }
                        )
                    )
                ),
                pl.col("figurecaption").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("figureref").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "attributes": REF_ID_STRUCT,
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                            }
                        )
                    )
                ),
                pl.col("formula").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "attributes": ID_ONLY_STRUCT,
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                            }
                        )
                    )
                ),
                pl.col("paragraph").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("publisher").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("sectionheader").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                                "attributes": SECTION_ATTR_STRUCT,
                            }
                        )
                    )
                ),
                pl.col("table").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("tableref").str.json_decode(
                    pl.List(
                        pl.Struct(
                            {
                                "attributes": REF_ID_STRUCT,
                                "end": pl.UInt32,
                                "start": pl.UInt32,
                            }
                        )
                    )
                ),
                pl.col("title").str.json_decode(pl.List(START_END_STRUCT)),
                pl.col("venue").str.json_decode(pl.List(START_END_STRUCT)),
            ]
        )
    )


def build_s2orc_lazyframe(input_glob: str, schema_sample: str | Path) -> pl.LazyFrame:
    """Build a lazy S2ORC frame with the fields needed by downstream scripts."""
    schema = infer_schema(schema_sample)
    lf = pl.scan_ndjson(input_glob, low_memory=True, schema=schema)

    selected_lf = lf.select(
        [
            pl.col("corpusid"),
            pl.col("externalids"),
            pl.col("content").struct.field("text").alias("text"),
            pl.col("content").struct.field("annotations").alias("annotations"),
        ]
    )

    return decode_annotations(selected_lf)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert raw S2ORC dataset parts into partitioned Parquet."
    )
    parser.add_argument(
        "--input-glob",
        default=DEFAULT_INPUT_GLOB,
        help="Glob for raw S2ORC parts. Default: s2orc/s2orc_part*.zip.",
    )
    parser.add_argument(
        "--schema-sample",
        default=DEFAULT_SCHEMA_SAMPLE,
        help="Single raw S2ORC part used for full schema inference. Default: s2orc/s2orc_part1.zip.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Output Parquet directory/file base. Default: s2orc.parquet.",
    )
    parser.add_argument(
        "--partition-size",
        type=int,
        default=DEFAULT_PARTITION_SIZE,
        help="Maximum rows per output partition. Default: 1000000.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the S2ORC conversion pipeline."""
    args = parse_args()
    lf = build_s2orc_lazyframe(args.input_glob, args.schema_sample)

    print(f"Writing partitioned Parquet output to {args.output}...")
    lf.sink_parquet(
        pl.PartitionMaxSize(args.output, max_size=args.partition_size),
        mkdir=True,
    )
    print("S2ORC processing complete.")


if __name__ == "__main__":
    main()
