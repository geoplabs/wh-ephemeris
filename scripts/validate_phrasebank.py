from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.content.phrasebank import AREAS, coverage_matrix

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "phrasebank" / "phrases.json"


def _load_entries(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("entries", [])


def _validate_clause(text: str, *, max_words: int = 28) -> list[str]:
    issues: list[str] = []
    stripped = text.strip()
    if not stripped:
        issues.append("clause is empty")
        return issues
    if not stripped[0].isupper():
        issues.append("clause must start with a capital letter")
    if not stripped.endswith((".", "!")):
        issues.append("clause must end with terminal punctuation")
    if "!" in stripped:
        issues.append("clause should not contain exclamation marks")
    words = stripped.rstrip(".!?").split()
    if len(words) > max_words:
        issues.append(f"clause exceeds {max_words} words")
    return issues


def _validate_template(text: str) -> list[str]:
    issues: list[str] = []
    stripped = text.strip()
    if "{phrase}" not in stripped:
        issues.append("template missing {phrase} placeholder")
    if stripped.count("{") != stripped.count("}"):
        issues.append("template has mismatched braces")
    if stripped.endswith(","):
        issues.append("template should not end with a comma")
    return issues


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    entries = _load_entries(path)
    seen = set()
    for entry in entries:
        archetype = entry.get("archetype")
        intensity = entry.get("intensity")
        area = entry.get("area")
        key = (archetype, intensity, area)
        if key in seen:
            errors.append(f"duplicate entry for {key}")
            continue
        seen.add(key)
        clauses = entry.get("clause_variants") or []
        if not clauses:
            errors.append(f"missing clauses for {key}")
        for clause in clauses:
            for issue in _validate_clause(clause):
                errors.append(f"{key} clause issue: {issue}")
        templates = (entry.get("bullet_templates") or {}).items()
        for mode, values in templates:
            if mode not in {"do", "avoid"}:
                errors.append(f"{key} unexpected mode '{mode}'")
            for template in values or []:
                for issue in _validate_template(template):
                    errors.append(f"{key} template issue ({mode}): {issue}")
    expected = coverage_matrix(area for area in AREAS)
    missing = expected - seen
    if missing:
        errors.append(f"missing combinations: {sorted(missing)}")
    extra_areas = {key[2] for key in seen} - set(AREAS)
    if extra_areas:
        errors.append(f"unexpected areas in entries: {sorted(extra_areas)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate phrasebank assets.")
    parser.add_argument("--path", type=Path, default=DATA_PATH)
    args = parser.parse_args()
    errors = validate(args.path)
    if errors:
        for issue in errors:
            print(f"ERROR: {issue}")
        return 1
    print("Phrasebank assets validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
