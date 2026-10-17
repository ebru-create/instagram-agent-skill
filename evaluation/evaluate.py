#!/usr/bin/env python3
"""Evaluate supplied hook labels locally; no collection, training or network."""

import argparse
from datetime import date
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import statistics


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scorer = load_module("evaluation_hookscore", ROOT / "skills/ig-reel/hookscore.py")
classifier = load_module("evaluation_swipe", ROOT / "skills/ig-viral/swipe.py")


def roc_auc(labels, scores):
    """Rank-sum AUROC with half credit for ties; None without both classes."""
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    if any(type(label) is not int or label not in (0, 1) for label in labels):
        raise ValueError("labels must be integer 0 or 1")
    if any(not isinstance(score, (int, float)) or not math.isfinite(score) for score in scores):
        raise ValueError("scores must be finite numbers")
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(zip(scores, labels))
    rank_sum = 0.0
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][0] == ordered[start][0]:
            end += 1
        average_rank = (start + 1 + end) / 2
        rank_sum += average_rank * sum(label for _, label in ordered[start:end])
        start = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def validate(dataset, formula_ids):
    if (not isinstance(dataset, dict) or type(dataset.get("schema_version")) is not int
            or dataset["schema_version"] != 1):
        raise ValueError("expected a dataset object with schema_version 1")
    metadata = dataset.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    for key in ("id", "task", "positive_label", "provenance", "usage_rights"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"metadata.{key} must be a non-empty string")
    if metadata.get("kind") not in ("fixture", "observational"):
        raise ValueError("metadata.kind must be fixture or observational")
    if metadata.get("split") not in ("development", "holdout"):
        raise ValueError("metadata.split must be development or holdout")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("rows must be a non-empty list")
    seen_ids, seen_hooks = set(), set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        for key in ("id", "account", "hook"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"row {index}: {key} must be a non-empty string")
        if row["id"] in seen_ids:
            raise ValueError(f"duplicate row id: {row['id']}")
        seen_ids.add(row["id"])
        language = row.get("language")
        if language not in formula_ids:
            raise ValueError(f"row {index}: language must be en or tr")
        if type(row.get("label")) is not int or row["label"] not in (0, 1):
            raise ValueError(f"row {index}: label must be integer 0 or 1")
        key = (language, row["account"].strip().casefold(), scorer.normalize(row["hook"]).strip())
        if key in seen_hooks:
            raise ValueError(f"row {index}: duplicate hook within the same language/account")
        seen_hooks.add(key)
        if "expected_formula" in row and row["expected_formula"] is not None:
            fid = row["expected_formula"]
            if type(fid) is not int or fid not in formula_ids[language]:
                raise ValueError(f"row {index}: expected_formula is not in this language's catalogue")
        if metadata["kind"] == "observational":
            for field in ("source", "observed_at"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f"row {index}: observational data requires {field}")
            try:
                date.fromisoformat(row["observed_at"])
            except ValueError as exc:
                raise ValueError(f"row {index}: observed_at must be an ISO date (YYYY-MM-DD)") from exc
    return metadata, rows


def summarize(rows):
    accounts = sorted({row["account"] for row in rows})
    groups = []
    for account in accounts:
        group = [row for row in rows if row["account"] == account]
        groups.append({"account": account, "n": len(group),
                       "positive_n": sum(row["label"] for row in group),
                       "auc": roc_auc([row["label"] for row in group], [row["score"] for row in group])})
    eligible = [group["auc"] for group in groups if group["auc"] is not None]
    annotated = [row for row in rows if "expected_formula" in row]
    predicted_annotated = [row for row in annotated if row["predicted_formula"] is not None]
    classified_n = sum(row["predicted_formula"] is not None for row in rows)

    def agreement(items):
        return sum(row["expected_formula"] == row["predicted_formula"] for row in items) / len(items) if items else None

    return {
        "n": len(rows), "positive_n": sum(row["label"] for row in rows),
        "negative_n": sum(row["label"] == 0 for row in rows),
        "pooled_auc": roc_auc([row["label"] for row in rows], [row["score"] for row in rows]),
        "within_account_macro_auc": statistics.mean(eligible) if eligible else None,
        "evaluable_accounts": len(eligible), "total_accounts": len(groups),
        "by_account": groups,
        "classification": {"classified_n": classified_n, "coverage": classified_n / len(rows),
                           "abstained_n": len(rows) - classified_n, "annotated_n": len(annotated),
                           "exact_annotation_agreement": agreement(annotated),
                           "classified_annotated_n": len(predicted_annotated),
                           "agreement_when_classified": agreement(predicted_annotated)},
    }


def evaluate(dataset, dataset_bytes):
    paths = {language: ROOT / "skills/ig-reel" / filename
             for language, filename in (("en", "hooks.json"), ("tr", "hooks.tr.json"))}
    formulas = {language: classifier.load_formulas(str(path), language) for language, path in paths.items()}
    if any(catalogue is None for catalogue in formulas.values()):
        raise ValueError("language formula catalogue missing or unreadable; use the full repository")
    metadata, rows = validate(dataset, {language: {fid for fid, _, _ in catalogue}
                                      for language, catalogue in formulas.items()})
    scored = []
    for row in rows:
        _, score, verdict, _ = scorer.run(row["hook"], row["language"])
        fid, _ = classifier.classify(row["hook"], formulas[row["language"]], row["language"])
        result = {key: row[key] for key in ("id", "language", "label")}
        # Normalize account grouping, without attempting to infer ownership.
        result["account"] = row["account"].strip().casefold()
        result.update(score=score, verdict=verdict, predicted_formula=fid)
        if "expected_formula" in row:
            result["expected_formula"] = row["expected_formula"]
        scored.append(result)
    scored.sort(key=lambda row: row["id"])
    sources = [Path(__file__).resolve(), ROOT / "skills/ig-reel/hookscore.py",
               ROOT / "skills/ig-viral/swipe.py", ROOT / "skills/ig-account/ig_language.py", *paths.values()]
    return {
        "schema_version": 1, "metadata": metadata,
        "limitations": ["Descriptive metrics only; no causal or view-prediction claim.",
                        "Fixture labels test the pipeline, not real-world performance." if metadata["kind"] == "fixture"
                        else "Observational labels and comparability must be reviewed by the dataset owner.",
                        "No confidence intervals estimated. Small, selected or tuned datasets can mislead.",
                        "Pooled AUROC may reflect account differences; review within-account results.",
                        "Classification coverage is not annotation agreement or accuracy."],
        "reproducibility": {"dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
                            "python": platform.python_version(),
                            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                              for path in sources}},
        "by_language": {language: summarize([row for row in scored if row["language"] == language])
                        for language in ("en", "tr") if any(row["language"] == language for row in scored)},
        "scored_rows": scored,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="JSON dataset with explicit binary labels and provenance")
    parser.add_argument("--out", type=Path, help="save the JSON report; otherwise print it")
    args = parser.parse_args()
    if args.out and args.out.resolve() == args.dataset.resolve():
        parser.error("output must not overwrite the input dataset")
    try:
        raw = args.dataset.read_bytes()
        report = evaluate(json.loads(raw), raw)
        rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
