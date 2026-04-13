# Import necessary packages
import sys
from pathlib import Path
import polars as pl
import argparse
import re
import os
from datetime import datetime
from typing import Tuple
#import llm_cite_write
#from llm_cite_write.config import S2AG_DIR
#import pandas as pd

# --- Configuration: Dictionaries and Constants ---

# Define list of exact matches for each of the sections
exact_match_map = {
    # Introduction
    "introduction": "introduction",

    "case report": "introduction",
    "case presentation": "introduction",
    "background": "introduction",
    "objective": "introduction",
    "objectives": "introduction",
    "motivation": "introduction",
    "problem": "introduction",
    "preliminaries": "introduction",
    "preamble": "introduction",
    "prologue": "introduction",
    "overview": "introduction",

    "hypothesis": "introduction",
    "hypotheses": "introduction",
    "problem statement": "introduction",
    "problem definition": "introduction",
    "problem formulation": "introduction",
    "research questions": "introduction",
    "research question": "introduction",
    
    # Literature review
    "background literature": "lit_review",
    "review of literature": "lit_review",

    "literature review": "lit_review",
    "related work": "lit_review",
    "related works": "lit_review",
    "similar work": "lit_review",
    "previous work": "lit_review",
    "previous works": "lit_review",
    "similar work": "lit_review",
    "related research": "lit_review",
    "similar research": "lit_review",
    "state of the art": "lit_review",
    "state-of-the-art": "lit_review",

    "theory": "lit_review",
    "theoretical framework": "lit_review",
    "theoretical background": "lit_review",
    "theoretical foundation": "lit_review",


    # Discussion
    "discussion": "discussion",
    "results and discussion": "discussion",
    "results and discussions": "results",
    "result and discussion": "results",
    "discussion and conclusions": "discussion",
    "discussion and conclusion": "discussion",
    "discussions": "discussion",
    "limitations": "discussion",
    "strengths and limitations": "discussion",
    "practical implications": "discussion",

    # Results
    "results": "results",
    "main results": "results",
    "result": "results",
    "experimental results": "results",
    "findings": "results",
    "simulation results": "results",

    "observations": "results",
    "outcomes": "results",

    #"analysis": "results",
    "evaluation": "results",    
    "experimental section": "results",

    # Conclusion
    "conclusion": "conclusion",
    "v. conclusion": "conclusion",
    "conclusion and recommendations": "conclusion",
    "iv. conclusion": "conclusion",
    "conclusions": "conclusion",
    "summary": "conclusion",

    "epilogue": "conclusion",
    "considerations": "conclusion",
    "final considerations": "conclusion",
    "recommendations": "conclusion",
    "recommendation": "conclusion",
    "outlook": "conclusion",
    "open questions": "conclusion",
    "perspective": "conclusion",

    "concluding remarks": "conclusion",
    "final remarks": "conclusion",
    "future work": "conclusion",
    "future directions": "conclusion",
    "further work": "conclusion",

    # Methods
    "methods": "methods",
    "materials and methods": "methods",
    "material and methods": "methods",
    "material and method": "methods",
    "methods and materials": "methods",
    "materials": 'methods',
    "methodology": "methods",
    "method": "methods",
    "research methodology": "methods",
    "research methods": "methods",
    "data and methods": "methods",
    "procedures": "methods",
    "procedure": "methods",

    "study setup": "methods",
    "study characteristics": "methods",
    "study design": "methods",
    "research design": "methods",
    "measures": "methods",
    "treatment": "methods",
    "design": "methods",
    "study area": "methods",
    "variables": "methods",
    "setting": "methods",
    "measurements": "methods",
    "evaluation metrics": "methods",
    "ablation study": "methods",
    "patients": "methods",
    "patient characteristics": "methods",
    "subjects": "methods",
    "participants": "methods",
    "samples": "methods",
    "study participants": "methods",
    "animals": "methods",
    "demographics": "methods",
    "recruitment": "methods",
    "implementation": "methods",
    "approach": "methods",
    "technical approach": "methods",
    "implementation details": "methods",
    "model architecture": "methods",
    "system architecture": "methods",
    "algorithm": "methods",
    "model": "methods",
    "the model": "methods",
    "data": "methods",
    "clinical trial": "methods",
    "clinical trials": "methods",

    "inclusion criteria": "methods",
    "exclusion criteria": "methods",
    "inclusion and exclusion criteria": "methods",
    "exclusion and inclusion criteria": "methods",

    "search strategy": "methods",
    "study selection": "methods",
    "statistics": "methods",

    "statistical analysis": "methods",
    "statistical analyses": "methods",
    "statistical methods": "methods",

    "experimental design": "methods",
    "experiment": "methods",
    "experiments": "methods",
    "experimental setup": "methods",
    "experimental set-up": "methods",
    "experimental procedures": "methods",
    "experimental apparatus": "methods",
    "experimental details": "methods",
    "experimental setting": "methods",

    "data analysis": "methods",
    "data collection": "methods",
    "data extraction": "methods",
    "data sources": "methods",
    "data source": "methods",
    "dataset": "methods",
    "datasets": "methods",

    "patients and methods": "methods",
    "subjects and methods": "methods",
    "study design and participants": "methods",
    "study population": "methods",

    "sample": "methods",
    "sample collection": "methods",
    "sample size": "methods",
    "sample preparation": "methods",
    "sampling": "methods",

    "western blot analysis": "methods",
    "western blotting": "methods",
    "immunohistochemistry": "methods",
    "cell culture": "methods",
    "cells": "methods",

    # Other
    "author": "other",
    "authors' contributions": "other",
    "author contributions": "other",
    
    "conflicts of interest": "other",
    "conflict of interest": "other",
    "declaration of competing interest": "other",
    "public interest statement": "other",
    "funding": "other",

    "data availability": "other",
    "data availability statement": "other",

    "ethical considerations": "other",
    "ethical approval": "other",
    "ethics statement": "other",
    "consent": "other",
    "compliance with ethical standards": "other",

    #ending
    "acknowledgments": "ending",
    "acknowledgements": "ending",
    "acknowledgment": "ending",
    "acknowledgement": "ending",
    "supporting information": "ending",
    "supplementary information": "ending",
    "supplementary material": "ending",
    "supplementary": "ending",
    "references": "ending",
    "abbreviations": "ending",
    
  #  "todos": "other",
  #  "continued": "other",
  #  "open access": "other",
  #  "dovepress": "other",
  #  "plos one": "other",
  #  "and": "other",
  #  "abstract": "other",
  #  "contributions": "other",

    #figure table
    "figure": "figure_table",
    "table":"figure_table"
}

# Define regex mapping, which will be used to search for words/terms in the headers
section_regex_map = {

    "introduction": r"\b("
                    r"introductions?|case (report|presentation)|preliminar(y|ies)|"
                    r"hypothes(is|es)|research questions?|"
                    # r"background|overview|" # I think these are too broad
                    r"problem (statement|definition|formulation)|(statement|definition|formulation) of the problem"
                    r")\b",

    "lit_review": r"\b("
                    r"theoretical (framework|background|foundation)|"
                    r"(related|previous|similar) (works?|research|literature)|"
                    r"literature review|state[- ]of[- ]the[- ]art"
                    r")\b",

    "methods": r"\b("
               r"methods?|methodolog(y|ies)|materials?|procedures?|protocols?|"
               #r"model|modeling|algorithm|approach|tools?|instruments?|data|variables|stimuli|" #these are very broad, but since methods are classified after everything, I think it is fine
               r"statistical (analysis|analyses|methods?)|"
               r"(study|research|experimental|simulations?|model|computational|experiments?) (design|protocols?|characteristics|strategy|selection|setup|set-up|description|site|populations?|participants?|subjects?|patients?|apparatus|details|setting)|"
               r"(patients?|participants?|subjects?) (recruitment|characteristics|demographics|populations?|groups?)|"
               r"data (analysis|analyses|description|collection|measurement|preprocessing|processing|acquisition|extraction|sources?)|datasets?|"
               r"population samples?|samples? (collection|sizes?|preparations?|processing|characteristics)|"
               r"(model|system|implementation|algorithm|technical) (architecture|approach|details?|implementations?|overview)|"
               r"proposed (models?|systems?|implementations?|algorithms?|architectures?|approach(es)?|stratetg(y|ies)|implementations?)|"
               r"(inclusion|exclusion) criteria"
               r")\b",

    "results": r"\b(results?|findings?|evaluations?|observations?|effects?)\b",
    
    "discussion": r"\b(discussions?|implications?|limitations?)\b",

    "conclusion": r"\b(conclusions?|further|future (works?|directions?|outlook|research)|summary|next steps|concluding remarks?)\b",

    "figure_table": r"\b(figures?|tables?|fig|charts?)\b", #graphs? probably not because would catch a lot of math and cs "graphs"

    "ending": r"\b("
             r"acknowledg(e|ements?)|references|bibliograph(y|ies)|"
             r"append(ix|ices)|(supplementary|supporting) (materials?|information)"
             r")\b",

    "other": r"\b("
             r"disclosures?|author contributions?|contribution statement|conflicts? of interests?|(competing|conflicting) interests?|"
             r"(ethics?|ethical) (statement|approval|considerations)|"
             r"(funding|sponsorship) (statement|declaration)|"
             r"(data|code) availability(?: (statement))?"
             r")\b"
}

# Define core sections of a paper (excludes "other" and "figure_table")
core_sections = {"introduction", "lit_review", "methods", "results", "discussion", "conclusion", "ending"}

# Define which sections are relevant
relevant_sections = {"introduction", "lit_review", "development", "methods", "results", "discussion", 'conclusion'}

# --- Processing Functions ---

def load_data(file_path: str | Path, n_rows: int | None = None) -> pl.LazyFrame:
    """
    Scans the Parquet file into a Polars LazyFrame for efficient processing.

    Using scan_parquet allows Polars to optimize queries without loading the
    entire dataset into memory upfront.

    Args:
        file_path: The path to the input S2AG Parquet file.
        n_rows: An optional integer to limit the number of rows scanned.
                This is highly recommended for quick testing and development.
                If set to None, the entire file will be processed.

    Returns:
        A Polars LazyFrame representing the data in the Parquet file.
    """
    print(f"⏳ Attempting to scan data from: {file_path}")

    # Ensure the path is a Path object for robust handling
    file_path = Path(file_path)

    if not file_path.exists():
        # Print an error message to standard error and exit if the file is not found.
        print(f"Error: Input file not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        # scan_parquet is used for memory-efficient lazy loading.
        # The n_rows argument is passed directly; if it's None, Polars scans the whole file.
        lf = pl.scan_parquet(file_path, n_rows=n_rows) # , low_memory=True
        print("✅ Successfully created a LazyFrame.")
        return lf
    except Exception as e:
        # Catch other potential errors during file scanning (e.g., corrupted file)
        print(f"❌ Error scanning Parquet file: {e}", file=sys.stderr)
        sys.exit(1)

def validate_input_schema(lf: pl.LazyFrame) -> None:
    """
    Validates that the LazyFrame contains all columns needed
    by the subsequent processing steps in this script.

    Args:
        lf: The Polars LazyFrame to validate.
    """
    print("⏳ Validating data schema...")

    # Hardcoded list of columns required by the section classification logic
    required_columns = ['corpusid', 'text', 'sectionheader']
    
    existing_columns = set(lf.columns)
    missing_columns = set(required_columns) - existing_columns

    if missing_columns:
        print(f"Error: The input data is missing required columns: {sorted(list(missing_columns))}", file=sys.stderr)
        print(f"Available columns are: {sorted(list(existing_columns))}", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ Schema validation passed. All required columns are present.")

def extract_and_process_sections(lf: pl.LazyFrame) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
    """
    Extracts and prepares the raw data for classification,
    splitting the data into a light metadata frame and a text frame,
    transforming into one row per section header, unnesting the section header information,
    extracting the header and section texts,
    and cleaning the header by removing list markers and standardizing the case.

    Args:
        lf: The raw LazyFrame with 'corpusid', 'text', and 'sectionheader' columns.

    Returns:
        A tuple containing two Lazyframes, each with one row per section:
        - processed_meta_lf: LazyFrame containing the extracted header title and metadata
        - text_lf: LazyFrame containing corpusid, row start position (for ordering), and row text
    """
    print("⏳ Extracting and processing sections...")

    # Regex to find list markers like "1.", "A)", "iv." at the start of a string.
    regex_pattern = r"^((?:[IVXLCDMivxlcdm]+|\d+|[A-Za-z])[.)])\s*"

    # Filter out rows with no text
    lf = lf.filter(~pl.col('text').is_null())

    # Isolate the text data. Calculate paper_len once and ensure one row per paper.
    text_lf = lf.select(
        "corpusid",
        "text",
        pl.col("text").str.len_chars().alias("paper_len")
    )
    
    # Isolate and process the metadata WITHOUT the text column
    meta_lf = (
        lf.select("corpusid", "sectionheader")
        .explode("sectionheader")
        .with_columns(
            pl.col('sectionheader').struct.field('start').cast(pl.Int64),
            pl.col('sectionheader').struct.field('end').cast(pl.Int64).alias('end_header'),
            pl.col('sectionheader').struct.field('attributes').struct.field('n').alias('section_n')
        )
        .drop("sectionheader")
        # Perform streamable deduplication on the small metadata frame.
        .group_by("corpusid", "start").first()
    )

    # Calculate section boundaries using the lightweight metadata.
    boundaries_lf = (
        meta_lf
        .join(text_lf.select("corpusid", "paper_len"), on="corpusid") # Join only paper_len
        .sort("corpusid", "start")
        .group_by("corpusid").agg(
            pl.col("start"),
            pl.col("paper_len").first()
        )
        .with_columns(
            end_section=(
                pl.col("start").list.slice(1).list.concat(pl.col("paper_len"))
            )
        )
        .drop("paper_len")
        .explode("start", "end_section")
        .rename({"start": "start"})
    )

    # Join text to the fully processed metadata.
    processed_meta_lf = (
        meta_lf
        .join(boundaries_lf, on=["corpusid", "start"])
        .join(text_lf, on="corpusid") # Join the text back in LAST
        .filter(pl.col("end_section") >= pl.col("start")) # Filter invalid sections
        .with_columns(
            # Perform slicing immediately after the text is available
            txt_header=pl.col('text').str.slice(pl.col('start'), pl.col('end_header') - pl.col('start'))
        )
        # Immediately drop the text column after use.
        .drop("text")
        .with_columns(
            section_number=pl.col("txt_header").str.extract(regex_pattern, 1),
            extracted=pl.col("txt_header")
            .str.replace(regex_pattern, "")
            .str.strip_chars()
            .str.to_lowercase()
        )
    )

    return processed_meta_lf, text_lf

def initial_mapping(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Performs the initial mapping of cleaned section headers to canonical labels
    
    Uses two strategies: a dictionary of exact matches for high
    precision and a series of regex patterns for broader matching. The exact
    match is prioritized. The output is an initial 'sec_map' column.

    Args:
        lf: The processed LazyFrame from the process_raw_sections step.

    Returns:
        A LazyFrame with a new 'sec_map' column containing the initial labels.
    """
    print("⏳ Performing initial mapping of section names...")

    # Map sections that contain words/terms in the regex
    # Ordered to avoid misclassifications like "Model results"
    contains_expression = (
        pl.when(pl.col("extracted").str.contains(section_regex_map["discussion"])).then(pl.lit("discussion"))
        .when(pl.col("extracted").str.contains(section_regex_map["conclusion"])).then(pl.lit("conclusion"))
        .when(pl.col("extracted").str.contains(section_regex_map["results"])).then(pl.lit("results"))
        .when(pl.col("extracted").str.contains(section_regex_map["ending"])).then(pl.lit("ending"))
        .when(pl.col("extracted").str.contains(section_regex_map["introduction"])).then(pl.lit("introduction"))
        .when(pl.col("extracted").str.contains(section_regex_map["lit_review"])).then(pl.lit("lit_review"))
        .when(pl.col("extracted").str.contains(section_regex_map["other"])).then(pl.lit("other"))
        # Methods contains the most terms; it's checked after the other main sections
        .when(pl.col("extracted").str.contains(section_regex_map["methods"])).then(pl.lit("methods"))
        .when(pl.col("extracted").str.contains(section_regex_map["figure_table"])).then(pl.lit("figure_table"))
        .otherwise(pl.lit(None)) # Use None for unclassified
    )

    # Apply both mapping strategies and then combine them.
    mapped_lf = lf.with_columns(
    # Based on the "contains" logic
    section_contains_match=contains_expression,

    # Based on the "exact match" logic
    section_exact_match=pl.col('extracted').replace_strict(exact_match_map, default=None),
    
    ).with_columns(
        # creates sec_map as the value of either exact or contains match columns
        # pl.coalesce takes the first non-null value, prioritizing the exact match.
        sec_map=pl.coalesce("section_exact_match", "section_contains_match")
    ).drop('section_exact_match', 'section_contains_match') # Dropping these columns as they are not needed anymore 

    return mapped_lf

def demarcate_end_matter(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Distinguishes between the main narrative and the end matter of a document.

    The logic basically is if there is a core section after sections like 'figure_table' or 'other',
    suppress it (set to null) so it can be absorbed by the preceding section label.
    Otherwise, it is considered part of the "end matter," and its label is kept.

    Args:
        lf: The LazyFrame from the initial_mapping step.

    Returns:
        A LazyFrame with a preliminary 'sec_label' column, where interstitial
        section labels have been set to null.
    """
    print("⏳ Demarcating end matter by last core section boundary...")

    # Create a temporary DataFrame to find the boundary for each paper.
    # This is a streamable group-by operation.
    boundary_lf = (
        lf.with_columns(
            is_core_section=pl.col("sec_map").is_in(core_sections)
        )
        .group_by("corpusid").agg(
            # Find the maximum 'start' position ONLY from core sections.
            pl.col("start").filter(pl.col("is_core_section")).max().alias("last_core_start")
        )
        # If a paper has no core sections, fill with 0 so all sections are kept.
        .with_columns(pl.col("last_core_start").fill_null(0))
    )

    # Join the boundary back and apply the labeling logic.
    return (
        lf
        # Join the calculated boundary value to each row.
        .join(boundary_lf, on="corpusid", how="left")
        .with_columns(
            # Apply the rule: keep the label if it's a core section OR
            # if it appears after the last core section. Otherwise, suppress it.
            sec_label=pl.when(
                pl.col("sec_map").is_in(core_sections) | (pl.col("start") > pl.col("last_core_start"))
            )
            .then(pl.col("sec_map"))  # Keep the label
            .otherwise(None)          # Suppress the label
        )
        # Clean up the intermediate column.
        .drop("last_core_start")
    )

def identify_development_section(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Identifies unlabeled, top-level headers that directly follow
    the 'introduction' or 'lit_review' sections. Such headers often represent
    content-specific titles for what is functionally a methods or literature review section.
    
    It also captures sections that do not fit into empirical-paper formats,
    like papers that have an introduction followed by a discussion/development of arguments

    By assigning these a "development" label, this function serves as
    a "catch-all" that effectively signals the end of the introductory part of a paper.

    Args:
        lf: The LazyFrame from the demarcate_end_matter step.

    Returns:
        A LazyFrame with an adjusted 'sec_label_new' column.
    """
    print("⏳ Labeling development sections...")

    # Step 1: Calculate 'top_header' heuristic and create a sequence index per paper.
    main_lf = (
        lf.with_columns(
            top_header=(
                pl.col("section_n").str.contains(r"^\d+\.?$") |
                pl.col("section_number").str.contains(r"^(X|XX|X?(IX|IV|V|V?I{1,3}))\.?\s*$") |
                pl.col("sec_map").is_in(core_sections)
            ).fill_null(False)
        )
        .sort("corpusid", "start")
        .with_columns(
            # A streamable way to create a row number within each group
            section_idx=pl.cum_count("corpusid")
        )
    )

    # Step 2: Create a lookup frame of previous sections with a new join key.
    prev_section_lf = main_lf.select(
        "corpusid",
        pl.col("sec_label").alias("prev_sec_label"),
        # Create a join key for the *next* row to find.
        # The row that was index 1 will now have a key of 2.
        (pl.col("section_idx") + 1).alias("join_idx")
    )

    # Step 3: Join the main frame with the previous section frame using the new key.
    return (
        main_lf
        .join(
            prev_section_lf,
            # The current row's index...
            left_on=["corpusid", "section_idx"],
            # ...matches the previous row's (index + 1).
            right_on=["corpusid", "join_idx"],
            how="left"
        )
        .with_columns(
            sec_label_new=pl.when(
                (pl.col('sec_label').is_null()) &
                (pl.col('top_header')) &
                (pl.col('prev_sec_label').is_in(['introduction', 'lit_review']))
            )
            .then(pl.lit('development'))
            .otherwise(pl.col('sec_label'))
        )
        .drop("section_idx", "prev_sec_label") # Clean up intermediate columns
    )

def propagate_labels(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Propagates the last recognized section label to subsequent unclassified sub-sections within a document
    
    It uses a forward-fill strategy to ensure every row with a null value
    is assigned to the most recent valid section header that appeared above it.
    
    Args:
        lf: The LazyFrame from the identify_development_section step.

    Returns:
        A LazyFrame with the 'sec_label_extended' column.
    """
    print("⏳ Propagating labels...")

    final_lf = lf.with_columns(
        pl.col('sec_label_new')
          .fill_null(strategy='forward')
          .over('corpusid', order_by='start')
          .alias('sec_label_extended')
    )
    
    return final_lf

def add_section_text(meta_lf: pl.LazyFrame, text_lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Joins the full text back to the classified metadata to extract section_text.

    This is the final step before aggregation, ensuring the large text column
    is handled only once.

    Args:
        meta_lf: The fully processed and classified metadata DataFrame.
        text_lf: The DataFrame containing just corpusid and the original text.

    Returns:
        A LazyFrame with the 'section_text' column added.
    """
    print("⏳ Assembling final data and extracting section text...")
    return (
        meta_lf
        .join(text_lf, on="corpusid", how="left")
        .with_columns(
            section_text=pl.col("text").str.slice(
                offset=pl.col("start"),
                length=pl.col("end_section") - pl.col("start")
            )
        )
        .drop("text") # Immediately drop the large text column
    )

def aggregate_text_by_section(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Groups rows by their final section label and aggregates their text
    to create one complete text block per section.

    Args:
        lf: The LazyFrame from the 'add_section_text' step.

    Returns:
        A LazyFrame where each row represents one complete section with its
        aggregated text.
    """

    print(f"⏳ Aggregating text snippets by section...")

    return (
        lf.group_by("corpusid", "sec_label_extended")
          .agg(
              # Aggregate text into a list of strings
              #  and join the list of text snippets into a single block.
              pl.col("section_text").implode().list.join(separator=" "),
              
              # Keep the minimum 'start' for each section to preserve order
              pl.col("start").min().alias("start"),

              # Keep the total paper length (it's the same for all rows in a group)
              pl.first("paper_len")
          )
          #.sort("corpusid", "start")
    )

def calculate_section_proportions(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculates each section's length as a percentage of the adjusted paper length.

    The "adjusted" length excludes terminal sections like 'ending' and 'other'
    to get a better measure of the core narrative's proportions,
    mainly because trailing sections are very long in many cases.

    Args:
        lf: The LazyFrame from the text aggregation step

    Returns:
        A LazyFrame with new columns for adjusted length and percentages.
    """
    print("⏳ Calculating section length proportions...")
    
    # Sections to exclude from the total length calculation for proportion metrics.
    excluded_from_total = ["ending", "other", "figure_table"]

    # Could also define it dynamically:
    #all_sections = set(section_regex_map.keys())
    #excluded_from_total = list(all_sections - relevant_sections)
    #print(f"Dynamically determined excluded sections: {excluded_from_total}")

    return (
        lf.with_columns(
            # Calculate section length
            section_length = pl.col("section_text").str.len_chars(),
        ).with_columns(
            # Identify the length of parts to exclude
            excluded_part=pl.when(pl.col("sec_label_extended").is_in(excluded_from_total))
                           .then(pl.col("section_length"))
                           .otherwise(0)
        )
        .with_columns(
            # Sum the excluded parts for each paper
            excluded_length=pl.col("excluded_part").sum().over("corpusid")
        )
        .with_columns(
            # Compute the adjusted paper length
            adjusted_paper_len=(pl.col("paper_len") - pl.col("excluded_length"))
        )
        .with_columns(
            # Calculate the percentage of each section against the new adjusted total
            perc_of_new_total=(
                (pl.col("section_length") / pl.col("adjusted_paper_len")) * 100
            )
        ).select(
            pl.col("*").exclude(["excluded_part", "excluded_length"])
        )
    )

def filter_by_quality_heuristics(
    lf: pl.LazyFrame,
    min_sections: int = 2, 
    max_section_perc: float = 80.0
) -> pl.LazyFrame:
    """
    Filters the dataset based on several quality and structure heuristics.

    Args:
        lf: The LazyFrame with calculated section proportions.
        min_sections: The minimum number of unique sections a paper must have.
        max_section_perc: The maximum percentage of the paper that any single
                          section can occupy.

    Returns:
        The final, filtered LazyFrame.
    """
    print(f"⏳ Filtering papers with quality heuristics (min_sections = {min_sections - 1}, max_perc = {max_section_perc})...")

    return lf.filter(
        # Paper must have more than (min_sections - 1) unique section types
        (pl.col("sec_label_extended").n_unique().over("corpusid") >= min_sections) &
        
        # The single largest section must not exceed the max percentage
        (pl.col("perc_of_new_total").max().over("corpusid") <= max_section_perc) &

        # The section type must be one of the relevant sections
        (pl.col("sec_label_extended").is_in(relevant_sections))
    )

# --- Main Execution ---
def main(
    input_path: str,
    output_dir: str,
    n_rows: int | None = None,
    min_sections: int = 2,
    max_section_perc: float = 80.0
):
    """
    Main function to orchestrate the pipeline for a single input file.
    """
    # --- Create the output directory structure ---
    base_output_path = Path(output_dir)
    classified_dir = base_output_path / "classified.parquet"
    aggregated_dir = base_output_path / "aggregated.parquet"
    filtered_dir = base_output_path / "filtered.parquet"

    # Ensure the directories exist
    classified_dir.mkdir(parents=True, exist_ok=True)
    aggregated_dir.mkdir(parents=True, exist_ok=True)
    filtered_dir.mkdir(parents=True, exist_ok=True)

    # --- Determine the output filename from the input path ---
    # e.g., "/path/to/0.parquet" -> "0.parquet"
    input_filename = Path(input_path).name

    # Define the full paths for the output files
    classified_path = classified_dir / input_filename
    aggregated_path = aggregated_dir / input_filename
    filtered_path = filtered_dir / input_filename

    # --- Run the Pipeline ---
    raw_lf = load_data(input_path, n_rows=n_rows)

    # Stage 1: Classification
    sections_lf, text_lf = extract_and_process_sections(raw_lf)
    sections_lf = initial_mapping(sections_lf)
    sections_lf = demarcate_end_matter(sections_lf)
    sections_lf = identify_development_section(sections_lf)
    sections_lf = propagate_labels(sections_lf)
    unaggregated_lf = add_section_text(sections_lf, text_lf)

    print(f"💾 Saving classified (unaggregated) results to: {classified_path}")
    unaggregated_lf.sink_parquet(classified_path)

    # Stage 2: Aggregation & Filtering
    # We now start from the file we just saved to keep memory low.
    aggregated_lf = aggregate_text_by_section(pl.scan_parquet(classified_path))
    proportions_lf = calculate_section_proportions(aggregated_lf)
    
    print(f"💾 Saving aggregated (unfiltered) results to: {aggregated_path}")
    proportions_lf.sink_parquet(aggregated_path)

    # We start from the new aggregated file.
    filtered_lf = filter_by_quality_heuristics(
        pl.scan_parquet(aggregated_path),
        min_sections=min_sections,
        max_section_perc=max_section_perc
    )

    print(f"💾 Saving final filtered results to: {filtered_path}")
    filtered_lf.sink_parquet(filtered_path)
    
    print(f"✅ Processing complete for {input_filename}.")

if __name__ == "__main__":
    # This block makes the script a runnable command-line tool.
    parser = argparse.ArgumentParser(description="Classify sections in S2ORC data.")
    
    # Input/Output arguments
    parser.add_argument("--input", type=str, required=True, help="Path to the input Parquet file.")
    parser.add_argument("--rows", type=int, default=None, help="Optional number of rows to process for testing.")
    parser.add_argument(
        "--output_dir", 
        type=str, 
        required=True, 
        help="Base directory to save a unique folder for this run's outputs and logs."
    )
    parser.add_argument(
        "--min_sections", 
        type=int, 
        default=2, 
        help="Filter out papers with fewer unique sections than this number. Default: 2."
    )
    parser.add_argument(
        "--max_perc", 
        type=float, 
        default=80.0, 
        help="Filter out papers where the largest section exceeds this percentage of the total. Default: 80.0."
    )

    args = parser.parse_args()
    
    main(
        input_path=args.input, 
        output_dir=args.output_dir, 
        n_rows=args.rows,
        min_sections=args.min_sections,
        max_section_perc=args.max_perc
    )