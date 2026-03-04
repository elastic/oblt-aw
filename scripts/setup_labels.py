import json
import logging
import os
import urllib.error
import urllib.request

from lib.workflow_common import read_json_file, split_repository, write_json_file
from summarize_results import create_setup_labels_report

LOGGER = logging.getLogger(__name__)


def load_active_labels() -> list[dict[str, str]]:
    config = read_json_file("active-labels.json")

    labels = config.get("labels", []) if isinstance(config, dict) else []
    if not isinstance(labels, list):
        raise ValueError("active-labels.json must contain a top-level 'labels' array")

    normalized_labels: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for item in labels:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        color = str(item.get("color", "")).strip()
        description = str(item.get("description", "")).strip()

        if not name or not color or not description:
            continue
        if name in seen_names:
            continue

        seen_names.add(name)
        normalized_labels.append(
            {
                "name": name,
                "color": color,
                "description": description,
            }
        )

    return normalized_labels


def create_label(token: str, owner: str, repo: str, label: dict[str, str]) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/labels"
    body = json.dumps(label).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "setup-labels-workflow",
        },
    )

    try:
        with urllib.request.urlopen(request):
            LOGGER.info("Created label %s in %s/%s", label["name"], owner, repo)
            return "created"
    except urllib.error.HTTPError as error:
        if error.code == 422:
            LOGGER.info("Label already exists: %s in %s/%s", label["name"], owner, repo)
            return "existing"

        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to create label {label['name']} in {owner}/{repo}: HTTP {error.code} {details}"
        ) from error


def write_report(report_path: str, report: dict[str, object]) -> None:
    write_json_file(report_path, report)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    report_path = os.environ.get("SETUP_LABELS_REPORT_PATH", "setup-labels-report.json").strip()
    target_repository = os.environ.get("TARGET_REPOSITORY", "").strip()
    if not report_path:
        report_path = "setup-labels-report.json"

    report = create_setup_labels_report(repos_total=1)

    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        LOGGER.error("Missing GH_TOKEN environment variable")
        report["error"] = "Missing GH_TOKEN environment variable"
        write_report(report_path, report)
        return 1

    if not target_repository:
        LOGGER.error("Missing TARGET_REPOSITORY environment variable")
        report["error"] = "Missing TARGET_REPOSITORY environment variable"
        write_report(report_path, report)
        return 1

    owner, repo = split_repository(target_repository)
    if not owner or not repo:
        LOGGER.error("Invalid TARGET_REPOSITORY value: %s", target_repository)
        report["error"] = f"Invalid TARGET_REPOSITORY value: {target_repository}"
        write_report(report_path, report)
        return 1

    try:
        labels = load_active_labels()

        LOGGER.info("Ensuring labels in %s/%s...", owner, repo)
        report["repos_processed"] = 1
        repository_name = f"{owner}/{repo}"
        repository_created = 0
        repository_existing = 0

        for label in labels:
            result = create_label(token, owner, repo, label)
            if result == "created":
                report["labels_created"] = int(report["labels_created"]) + 1
                repository_created += 1
            elif result == "existing":
                report["labels_existing"] = int(report["labels_existing"]) + 1
                repository_existing += 1

        report["per_repository"] = [
            {
                "repository": repository_name,
                "status": "processed",
                "labels_created": repository_created,
                "labels_existing": repository_existing,
            }
        ]
    except Exception as error:
        report["error"] = str(error)
        report["per_repository"] = [
            {
                "repository": target_repository,
                "status": "failed",
                "labels_created": 0,
                "labels_existing": 0,
            }
        ]
        write_report(report_path, report)
        LOGGER.exception("Failed to setup labels")
        return 1

    report["status"] = "success"
    write_report(report_path, report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
