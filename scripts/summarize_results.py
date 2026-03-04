import argparse
import os
from pathlib import Path
from typing import Any

from lib.workflow_common import read_json_file

SETUP_LABELS_REPORT_TEMPLATE: dict[str, Any] = {
    "status": "failed",
    "repos_total": 1,
    "repos_processed": 0,
    "repos_skipped": 0,
    "labels_created": 0,
    "labels_existing": 0,
    "per_repository": [],
    "error": "",
}

SETUP_LABELS_AGGREGATE_TEMPLATE: dict[str, Any] = {
    "repos_total": 0,
    "repos_processed": 0,
    "repos_skipped": 0,
    "labels_created": 0,
    "labels_existing": 0,
    "per_repository": [],
    "errors": [],
}


def create_setup_labels_report(repos_total: int = 1) -> dict[str, Any]:
    report = dict(SETUP_LABELS_REPORT_TEMPLATE)
    report["repos_total"] = repos_total
    report["per_repository"] = []
    return report


def aggregate_setup_labels_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = dict(SETUP_LABELS_AGGREGATE_TEMPLATE)
    aggregate["per_repository"] = []
    aggregate["errors"] = []

    for item in reports:
        aggregate["repos_total"] += int(item.get("repos_total", 0))
        aggregate["repos_processed"] += int(item.get("repos_processed", 0))
        aggregate["repos_skipped"] += int(item.get("repos_skipped", 0))
        aggregate["labels_created"] += int(item.get("labels_created", 0))
        aggregate["labels_existing"] += int(item.get("labels_existing", 0))

        per_repository = item.get("per_repository", [])
        if isinstance(per_repository, list):
            aggregate["per_repository"].extend(per_repository)

        error = str(item.get("error", "")).strip()
        if error:
            aggregate["errors"].append(error)

    return aggregate


def emit_workflow_annotation(level: str, title: str, message: str) -> None:
    annotation_level = "notice" if level not in {"notice", "error", "warning"} else level
    print(f"::{annotation_level} title={title}::{message}")


def append_step_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not summary_path:
        raise SystemExit("GITHUB_STEP_SUMMARY is not set")

    with open(summary_path, "a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines) + "\n")


def parse_result_line(line: str) -> tuple[str, str, str]:
    parts = line.split("|", 2)
    if len(parts) != 3:
        return "-", "invalid", "-"
    return parts[0].strip(), parts[1].strip(), parts[2].strip()


def summarize_pr_results() -> int:
    report_files = sorted(Path("pr-results").glob("*.txt"))
    lines: list[str] = []

    for report_file in report_files:
        with report_file.open("r", encoding="utf-8") as file:
            for line in file:
                value = line.strip()
                if value:
                    lines.append(value)

    lines.sort()

    parts = []
    for line in lines:
        repository, operation, _ = parse_result_line(line)
        parts.append(f"{repository} ({operation})")

    annotation = ", ".join(parts) if parts else "No PR results found"
    emit_workflow_annotation("notice", "PR Distribution Results", annotation)

    summary_lines = [
        "## PR Distribution Results",
        "",
        "| Repository | Operation | Pull Request |",
        "| --- | --- | --- |",
    ]

    for line in lines:
        repository, operation, url = parse_result_line(line)
        if url.startswith("http"):
            pull_request = f"[{url}]({url})"
        else:
            pull_request = "—"
        summary_lines.append(f"| `{repository}` | {operation} | {pull_request} |")

    append_step_summary(summary_lines)
    return 0


def summarize_label_results() -> int:
    results_dir = os.environ.get("SETUP_LABELS_RESULTS_DIR", "setup-label-results")
    has_repositories = os.environ.get("SETUP_LABELS_HAS_REPOSITORIES", "false")
    job_result = os.environ.get("SETUP_LABELS_JOB_RESULT", "skipped")

    report_files = sorted(Path(results_dir).glob("*.json")) if has_repositories == "true" else []

    reports = []
    for report_file in report_files:
        reports.append(read_json_file(report_file))

    report = aggregate_setup_labels_reports(reports)

    title = "Setup Labels Results"
    summary_line = (
        f"outcome={job_result}; repos total={report['repos_total']}, processed={report['repos_processed']}, "
        f"skipped={report['repos_skipped']}; labels created={report['labels_created']}, "
        f"existing={report['labels_existing']}"
    )

    if has_repositories != "true":
        emit_workflow_annotation("notice", title, "No repositories to process")
    elif job_result == "success":
        emit_workflow_annotation("notice", title, summary_line)
    else:
        error_text = "; ".join(report["errors"]) or "Setup labels matrix job failed"
        emit_workflow_annotation("error", title, f"{summary_line}; error={error_text}")

    summary_lines = [
        "## Setup labels summary",
        "",
        f"- Matrix job outcome: `{job_result}`",
        f"- Repositories total: {report['repos_total']}",
        f"- Repositories processed: {report['repos_processed']}",
        f"- Repositories skipped: {report['repos_skipped']}",
        f"- Labels created: {report['labels_created']}",
        f"- Labels already existing: {report['labels_existing']}",
    ]
    if report["errors"]:
        summary_lines.append(f"- Errors: {'; '.join(report['errors'])}")

    per_repository = report.get("per_repository")
    if isinstance(per_repository, list) and per_repository:
        summary_lines.extend(
            [
                "",
                "### Per-repository breakdown",
                "",
                "| Repository | Status | Created | Existing |",
                "| --- | --- | ---: | ---: |",
            ]
        )
        for item in per_repository:
            repository = str(item.get("repository", "-"))
            status = str(item.get("status", "-"))
            created = int(item.get("labels_created", 0))
            existing = int(item.get("labels_existing", 0))
            summary_lines.append(f"| `{repository}` | {status} | {created} | {existing} |")

    append_step_summary(summary_lines)

    if has_repositories != "true":
        return 0

    return 0 if job_result == "success" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize workflow results")
    parser.add_argument(
        "--mode",
        choices=["pr", "labels"],
        required=True,
        help="Summary mode: 'pr' for distribution PR results or 'labels' for setup-label results",
    )
    args = parser.parse_args()

    if args.mode == "pr":
        return summarize_pr_results()

    return summarize_label_results()


if __name__ == "__main__":
    raise SystemExit(main())
