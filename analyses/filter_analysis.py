"""
Quality-filter threshold analysis for section classification outputs.

This script studies two paper-level signals used to identify likely bad
section-classifier outputs:

1. longest_section_percent:
   The percentage of a paper's relevant-section text taken by the largest
   classified section.

2. n_sections:
   The number of relevant section labels assigned to the paper.

It then tests IQR-based and percentile-based cutoffs and measures how many
papers are retained and how F1 changes on an evaluation set.

Typical runs:

    python analyses/quality_filter_threshold_analysis.py \
        --label-source human \
        --output-dir analyses/quality_filter_human

    python analyses/quality_filter_threshold_analysis.py \
        --label-source llm \
        --output-dir analyses/quality_filter_llm
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RELEVANT_SECTIONS = [
    "introduction",
    "lit_review",
    "development",
    "methods",
    "results",
    "discussion",
    "conclusion",
]


def macro_f1(y_true: pd.Series, y_pred: pd.Series, labels: list[str]) -> float:
    """Compute macro F1 without requiring sklearn."""
    scores = []

    for label in labels:
        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append(f1)

    return float(np.mean(scores)) if scores else float("nan")


def weighted_f1(y_true: pd.Series, y_pred: pd.Series, labels: list[str]) -> float:
    """Compute weighted F1, weighted by support of each true label."""
    scores = []
    weights = []

    for label in labels:
        support = int((y_true == label).sum())
        if support == 0:
            continue

        tp = int(((y_true == label) & (y_pred == label)).sum())
        fp = int(((y_true != label) & (y_pred == label)).sum())
        fn = int(((y_true == label) & (y_pred != label)).sum())

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

        scores.append(f1)
        weights.append(support)

    return float(np.average(scores, weights=weights)) if weights else float("nan")


def load_paper_metrics(section_labels_path: Path) -> pd.DataFrame:
    """
    Load classifier section outputs and aggregate them to one row per paper.

    Expected input columns:
        corpusid
        section_length
        sec_label_extended

    The output contains:
        corpusid
        total_section_length
        longest_section_length
        n_sections
        longest_section_percent
    """
    table = pq.read_table(
        section_labels_path,
        columns=["corpusid", "section_length", "sec_label_extended"],
    )

    # Keep only section labels that are part of the main classifier vocabulary.
    mask = pc.is_in(
        table["sec_label_extended"],
        value_set=pa.array(RELEVANT_SECTIONS, type=pa.large_string()),
    )
    table = table.filter(mask)

    # Aggregate all relevant sections for each paper.
    grouped = table.group_by("corpusid").aggregate(
        [
            ("section_length", "sum"),
            ("section_length", "max"),
            ("section_length", "count"),
        ]
    )

    paper_metrics = grouped.to_pandas().rename(
        columns={
            "section_length_sum": "total_section_length",
            "section_length_max": "longest_section_length",
            "section_length_count": "n_sections",
        }
    )

    paper_metrics["longest_section_percent"] = (
        paper_metrics["longest_section_length"]
        / paper_metrics["total_section_length"]
        * 100.0
    )

    return paper_metrics.sort_values("corpusid").reset_index(drop=True)


def load_human_eval_rows(
    section_labels_path: Path,
    annotations_path: Path,
    paper_sections_path: Path,
    paper_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a validation table using Prolific annotations.

    Human labels are reduced to a majority label per paper section. These are
    joined to classifier rows using paper_id + section start position.
    """
    annotations = pd.read_csv(annotations_path)
    paper_sections = pd.read_csv(
        paper_sections_path,
        usecols=["id", "paper_id", "start_position", "extracted_headers"],
    )

    # Remove annotations that should not count as section-label judgments.
    annotations = annotations[
        (annotations["is_other_language"] == 0)
        & (annotations["is_annotator_confused"] == 0)
        & (annotations["label"].isin(RELEVANT_SECTIONS))
    ].copy()

    # Majority vote per paper section.
    votes = (
        annotations.groupby(["paper_id", "section_id", "label"], as_index=False)
        .size()
        .rename(columns={"size": "votes"})
    )
    votes["total_votes"] = votes.groupby(["paper_id", "section_id"])["votes"].transform("sum")
    votes["vote_share"] = votes["votes"] / votes["total_votes"]

    majority = (
        votes.sort_values(
            ["paper_id", "section_id", "votes", "label"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["paper_id", "section_id"], keep="first")
        .merge(
            paper_sections,
            left_on=["paper_id", "section_id"],
            right_on=["paper_id", "id"],
            how="left",
        )
    )

    # Read only classifier rows for papers that appear in the validation set.
    paper_ids = majority["paper_id"].dropna().astype("int64").unique().tolist()
    dataset = ds.dataset(section_labels_path, format="parquet")

    classifier_rows = dataset.to_table(
        columns=["corpusid", "start", "section_length", "sec_label_extended"],
        filter=pc.field("corpusid").isin(paper_ids),
    ).to_pandas()

    # Match human section ids to classifier section starts.
    eval_rows = majority.merge(
        classifier_rows,
        left_on=["paper_id", "start_position"],
        right_on=["corpusid", "start"],
        how="inner",
    )

    # Attach paper-level filter metrics.
    eval_rows = eval_rows.merge(
        paper_metrics[["corpusid", "longest_section_percent", "n_sections"]].rename(
            columns={"corpusid": "paper_id"}
        ),
        on="paper_id",
        how="left",
    )

    return eval_rows


def extract_llm_response(response_row: dict) -> tuple[str | None, str | None]:
    """Parse one OpenAI batch-result JSON object."""
    try:
        output = response_row["response"]["body"]["output"]
        message = next(item for item in output if item.get("type") == "message")
        text = message["content"][0]["text"]
        parsed = json.loads(text)
        return parsed.get("label"), parsed.get("confidence")
    except Exception:
        return None, None


def load_llm_eval_rows(
    auto_eval_sample_path: Path,
    llm_results_dir: Path,
    paper_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a validation table using LLM annotations.

    The batch custom_id was created as:
        corpusid-index_within_paper

    So we reconstruct the same ids from auto_eval_sample.parquet, then join
    them to the JSONL batch outputs.
    """
    sample = pq.read_table(
        auto_eval_sample_path,
        columns=["corpusid", "start", "section_text", "sec_label_extended"],
    ).to_pandas()

    # Match the filtering used before the LLM batch was created.
    sample = sample[
        (sample["section_text"].fillna("").astype(str).str.strip() != "")
        & (~sample["sec_label_extended"].isin(["figure_table", "ending", "other"]))
    ].copy()

    mapped_rows = []
    for paper_id, group in sample.groupby("corpusid"):
        group = group.reset_index(drop=True)

        for index, row in group.iterrows():
            mapped_rows.append(
                {
                    "custom_id": f"{paper_id}-{index}",
                    "paper_id": int(row["corpusid"]),
                    "start": int(row["start"]),
                    "sec_label_extended": row["sec_label_extended"],
                }
            )

    mapping = pd.DataFrame(mapped_rows)

    llm_rows = []
    for path in sorted(llm_results_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                row = json.loads(line)
                label, confidence = extract_llm_response(row)

                llm_rows.append(
                    {
                        "custom_id": row.get("custom_id"),
                        "label": label,
                        "llm_confidence": confidence,
                    }
                )

    llm = pd.DataFrame(llm_rows).dropna(subset=["custom_id", "label"])
    llm = llm.drop_duplicates("custom_id", keep="last")

    eval_rows = mapping.merge(llm, on="custom_id", how="inner")

    eval_rows = eval_rows.merge(
        paper_metrics[["corpusid", "longest_section_percent", "n_sections"]].rename(
            columns={"corpusid": "paper_id"}
        ),
        on="paper_id",
        how="left",
    )

    return eval_rows


def score_subset(eval_rows: pd.DataFrame, labels: list[str]) -> dict[str, float | int]:
    """Compute F1 scores for the currently retained validation rows."""
    metric_rows = eval_rows[
        eval_rows["label"].isin(labels)
        & eval_rows["sec_label_extended"].isin(labels)
    ]

    return {
        "eval_papers": int(metric_rows["paper_id"].nunique()),
        "eval_sections": int(len(metric_rows)),
        "macro_f1": macro_f1(metric_rows["label"], metric_rows["sec_label_extended"], labels)
        if len(metric_rows)
        else np.nan,
        "weighted_f1": weighted_f1(metric_rows["label"], metric_rows["sec_label_extended"], labels)
        if len(metric_rows)
        else np.nan,
    }


def make_thresholds(values: pd.Series) -> pd.DataFrame:
    """
    Create threshold candidates.

    IQR thresholds are Q3 + k*IQR.
    Percentile thresholds are direct quantiles of longest_section_percent.
    """
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    iqr_rows = [
        {
            "strategy": "iqr",
            "parameter": f"k={k:.2f}",
            "threshold": min(100.0, q3 + k * iqr),
        }
        for k in np.arange(0.0, 3.01, 0.25)
    ]

    percentile_rows = [
        {
            "strategy": "percentile",
            "parameter": f"p={p:.1f}",
            "threshold": values.quantile(p / 100.0),
        }
        for p in list(np.arange(50.0, 95.1, 2.5)) + [96.0, 97.0, 98.0, 99.0]
    ]

    thresholds = pd.DataFrame(iqr_rows + percentile_rows)
    thresholds["threshold"] = thresholds["threshold"].clip(0, 100)

    return thresholds.drop_duplicates(["strategy", "threshold"]).sort_values(
        ["strategy", "threshold"]
    )


def threshold_grid(
    paper_metrics: pd.DataFrame,
    eval_rows: pd.DataFrame,
    thresholds: pd.DataFrame,
    min_sections_values: list[int],
) -> pd.DataFrame:
    """
    Evaluate all threshold candidates for each minimum-section rule.

    This gives one row per:
        cutoff strategy x cutoff value x min_sections value
    """
    rows = []
    total_papers = len(paper_metrics)
    labels = sorted(RELEVANT_SECTIONS)

    for min_sections in min_sections_values:
        for row in thresholds.itertuples(index=False):
            retained_papers = paper_metrics[
                (paper_metrics["n_sections"] >= min_sections)
                & (paper_metrics["longest_section_percent"] <= row.threshold)
            ]

            retained_ids = set(retained_papers["corpusid"].to_numpy())
            retained_eval = eval_rows[eval_rows["paper_id"].isin(retained_ids)]
            scores = score_subset(retained_eval, labels)

            rows.append(
                {
                    "strategy": row.strategy,
                    "parameter": row.parameter,
                    "threshold": row.threshold,
                    "min_sections": min_sections,
                    "retained_papers": int(len(retained_papers)),
                    "retention_rate": len(retained_papers) / total_papers,
                    **scores,
                }
            )

    return pd.DataFrame(rows)


def stable_choice(grid: pd.DataFrame, tolerance: float = 0.01) -> pd.DataFrame:
    """
    Pick the largest retained dataset within 1 percentage point of best macro F1.

    This is done separately for each strategy and min_sections setting.
    """
    choices = []

    for (strategy, min_sections), subset in grid.groupby(["strategy", "min_sections"]):
        best_f1 = subset["macro_f1"].max()
        candidates = subset[subset["macro_f1"] >= best_f1 - tolerance]

        if candidates.empty:
            continue

        choices.append(
            candidates.sort_values(
                ["retained_papers", "threshold"],
                ascending=[False, False],
            ).head(1)
        )

    return pd.concat(choices, ignore_index=True) if choices else pd.DataFrame()


def plot_distributions(paper_metrics: pd.DataFrame, output_dir: Path) -> None:
    """Plot the two paper-level quantities used by the filter."""
    output_dir.mkdir(parents=True, exist_ok=True)

    longest_values = paper_metrics["longest_section_percent"].sort_values().to_numpy()
    section_counts = paper_metrics["n_sections"].to_numpy()

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    axes[0, 0].hist(longest_values, bins=60, color="#4C78A8", edgecolor="white")
    axes[0, 0].axvline(80, color="#E45756", linestyle="--", label="current 80%")
    axes[0, 0].set_title("Longest section percent")
    axes[0, 0].set_xlabel("Largest relevant section / relevant section total (%)")
    axes[0, 0].set_ylabel("Documents")
    axes[0, 0].legend()

    ecdf_y = np.arange(1, len(longest_values) + 1) / len(longest_values)
    axes[0, 1].plot(longest_values, ecdf_y, color="#54A24B")
    axes[0, 1].axvline(80, color="#E45756", linestyle="--")
    axes[0, 1].set_title("ECDF: longest section percent")
    axes[0, 1].set_xlabel("Threshold (%)")
    axes[0, 1].set_ylabel("Share of documents <= threshold")

    bins = np.arange(0.5, int(section_counts.max()) + 1.5, 1)
    axes[1, 0].hist(section_counts, bins=bins, color="#F58518", edgecolor="white")
    axes[1, 0].axvline(2, color="#E45756", linestyle="--", label="min 2")
    axes[1, 0].axvline(3, color="#333333", linestyle="--", label="min 3")
    axes[1, 0].set_title("Number of relevant sections per document")
    axes[1, 0].set_xlabel("Number of relevant sections")
    axes[1, 0].set_ylabel("Documents")
    axes[1, 0].legend()

    min_values = np.arange(1, int(section_counts.max()) + 1)
    retained_share = [(section_counts >= value).mean() for value in min_values]
    axes[1, 1].step(min_values, retained_share, where="post", color="#B279A2")
    axes[1, 1].axvline(2, color="#E45756", linestyle="--")
    axes[1, 1].axvline(3, color="#333333", linestyle="--")
    axes[1, 1].set_title("Retention by minimum section count")
    axes[1, 1].set_xlabel("Minimum section count")
    axes[1, 1].set_ylabel("Share of documents retained")

    fig.tight_layout()
    fig.savefig(output_dir / "distribution_longest_section_and_section_count.png", dpi=200)
    plt.close(fig)


def plot_grid(grid: pd.DataFrame, output_dir: Path) -> None:
    """Plot retained dataset size and F1 across threshold values."""
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, strategy in zip(axes, ["percentile", "iqr"]):
        subset = grid[grid["strategy"] == strategy].sort_values("threshold")
        ax2 = ax.twinx()

        for min_sections, part in subset.groupby("min_sections"):
            linestyle = "-" if min_sections == 2 else "--"

            ax.plot(
                part["threshold"],
                part["retention_rate"],
                color="#4C78A8",
                marker="o",
                linestyle=linestyle,
                label=f"Retention, min {min_sections}",
            )

            ax2.plot(
                part["threshold"],
                part["macro_f1"],
                color="#E45756",
                marker="o",
                linestyle=linestyle,
                label=f"Macro F1, min {min_sections}",
            )

        ax.axvline(80, color="#333333", linestyle="--", alpha=0.6)
        ax.set_title(f"{strategy.title()} cutoff grid")
        ax.set_xlabel("Longest-section threshold (%)")
        ax.set_ylabel("Retained document share", color="#4C78A8")
        ax2.set_ylabel("Macro F1", color="#E45756")
        ax.tick_params(axis="y", labelcolor="#4C78A8")
        ax2.tick_params(axis="y", labelcolor="#E45756")
        ax.legend(loc="lower left", fontsize=8)
        ax2.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_dir / "grid_retention_and_f1_by_threshold.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))

    for (strategy, min_sections), part in grid.groupby(["strategy", "min_sections"]):
        ax.plot(
            part["retention_rate"],
            part["macro_f1"],
            marker="o",
            label=f"{strategy}, min {min_sections}",
        )

    ax.set_title("Quality-size tradeoff")
    ax.set_xlabel("Retained document share")
    ax.set_ylabel("Macro F1")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "quality_size_tradeoff.png", dpi=200)
    plt.close(fig)


def write_summary(
    output_dir: Path,
    paper_metrics: pd.DataFrame,
    eval_rows: pd.DataFrame,
    grid: pd.DataFrame,
    stable: pd.DataFrame,
    label_source: str,
    min_sections_values: list[int],
) -> None:
    """Write a compact Markdown summary of the run."""
    output_dir.mkdir(parents=True, exist_ok=True)

    def table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_No rows._"

        display = df.copy()
        for col in display.select_dtypes(include=[np.number]).columns:
            if col in {"retained_papers", "eval_papers", "eval_sections", "min_sections"}:
                display[col] = display[col].map(lambda x: f"{x:,.0f}")
            else:
                display[col] = display[col].map(lambda x: f"{x:.4f}")

        headers = list(display.columns)
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]

        for row in display.itertuples(index=False):
            lines.append("| " + " | ".join(str(value) for value in row) + " |")

        return "\n".join(lines)

    values = paper_metrics["longest_section_percent"]
    counts = paper_metrics["n_sections"]

    current_80 = (
        grid.assign(distance_from_80=(grid["threshold"] - 80).abs())
        .sort_values(["min_sections", "strategy", "distance_from_80"])
        .groupby(["strategy", "min_sections"])
        .head(1)
        .drop(columns=["distance_from_80"])
    )

    best_rows = grid.sort_values("macro_f1", ascending=False).head(10)

    lines = [
        "# Quality Filter Threshold Analysis",
        "",
        f"- Label source: {label_source}",
        f"- Full documents analyzed: {len(paper_metrics):,}",
        f"- Validation sections: {len(eval_rows):,}",
        f"- Validation papers: {eval_rows['paper_id'].nunique():,}",
        f"- Minimum section rules tested: {', '.join(map(str, min_sections_values))}",
        "",
        "## Longest Section Percent",
        "",
        f"- median: {values.median():.2f}%",
        f"- p75: {values.quantile(0.75):.2f}%",
        f"- p90: {values.quantile(0.90):.2f}%",
        f"- p95: {values.quantile(0.95):.2f}%",
        f"- p99: {values.quantile(0.99):.2f}%",
        "",
        "## Number of Sections",
        "",
        f"- median: {counts.median():.0f}",
        f"- share with >= 2 sections: {(counts >= 2).mean():.3f}",
        f"- share with >= 3 sections: {(counts >= 3).mean():.3f}",
        "",
        "## Current 80% Reference",
        "",
        table(current_80),
        "",
        "## Best F1 Rows",
        "",
        table(best_rows),
        "",
        "## Stable Choices",
        "",
        "Stable means the largest retained dataset within 1 percentage point of the best macro F1 for that strategy and min-section setting.",
        "",
        table(stable),
        "",
    ]

    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--section-labels",
        type=Path,
        default=Path("dataset/section_labels.parquet"),
        help="Classifier section-label parquet file.",
    )

    parser.add_argument(
        "--label-source",
        choices=["human", "llm"],
        default="human",
        help="Evaluation labels to use for F1 curves.",
    )

    parser.add_argument(
        "--annotations",
        type=Path,
        default=Path("prolific_annotations/prolific_all_annotations.csv"),
        help="Human annotation CSV.",
    )

    parser.add_argument(
        "--paper-sections",
        type=Path,
        default=Path("prolific_annotations/paper_sections.csv"),
        help="CSV linking Prolific section ids to paper/start positions.",
    )

    parser.add_argument(
        "--auto-eval-sample",
        type=Path,
        default=Path("llm_annotations/auto_eval_sample.parquet"),
        help="Sample used to create LLM annotation batches.",
    )

    parser.add_argument(
        "--llm-results-dir",
        type=Path,
        default=Path("llm_annotations/output/run_20260416_005312"),
        help="Directory containing LLM batch result JSONL files.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analyses/quality_filter_threshold_outputs"),
    )

    parser.add_argument(
        "--min-sections-values",
        type=int,
        nargs="+",
        default=[2, 3],
        help="Minimum section-count rules to test.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading paper-level metrics...")
    paper_metrics = load_paper_metrics(args.section_labels)
    paper_metrics.to_csv(args.output_dir / "paper_quality_metrics.csv", index=False)

    print("Loading evaluation labels...")
    if args.label_source == "human":
        eval_rows = load_human_eval_rows(
            args.section_labels,
            args.annotations,
            args.paper_sections,
            paper_metrics,
        )
    else:
        eval_rows = load_llm_eval_rows(
            args.auto_eval_sample,
            args.llm_results_dir,
            paper_metrics,
        )

    eval_rows.to_csv(args.output_dir / "validation_joined_rows.csv", index=False)

    print("Running threshold grid...")
    thresholds = make_thresholds(paper_metrics["longest_section_percent"])
    thresholds.to_csv(args.output_dir / "cutoff_thresholds.csv", index=False)

    grid = threshold_grid(
        paper_metrics,
        eval_rows,
        thresholds,
        args.min_sections_values,
    )
    grid.to_csv(args.output_dir / "cutoff_grid_results.csv", index=False)

    stable = stable_choice(grid)
    stable.to_csv(args.output_dir / "stable_cutoff_choices.csv", index=False)

    print("Creating plots...")
    plot_distributions(paper_metrics, args.output_dir)
    plot_grid(grid, args.output_dir)

    write_summary(
        args.output_dir,
        paper_metrics,
        eval_rows,
        grid,
        stable,
        args.label_source,
        args.min_sections_values,
    )

    print(f"Done. Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()