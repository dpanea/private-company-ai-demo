from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from pcad.models import Account, UserOwner


REFERENCE_DATE = "2026-05-13"
CSV_MODELS = {"users": UserOwner, "accounts": Account}


def test_generate_synthetic_cli_creates_complete_manifest(tmp_path: Path) -> None:
    output = tmp_path / "synthetic"
    _run_generator(output)
    manifest = _load_manifest(output)

    assert manifest["reference_date"] == REFERENCE_DATE
    assert len(manifest["accounts"]) == 3
    assert manifest["internal_knowledge"]["account_id"] == "SYN_ACC_INTERNAL"
    assert manifest["internal_knowledge"]["account_name"] == "Internal company knowledge"
    assert len(manifest["internal_knowledge"]["artifacts"]) == 4
    assert set(manifest["crm"]) == set(CSV_MODELS)

    requires_ocr = []
    for account in manifest["accounts"]:
        artifacts = account["artifacts"]
        assert len([artifact for artifact in artifacts if artifact["format"] == "pdf"]) >= 2
        assert len([artifact for artifact in artifacts if artifact["format"] == "markdown"]) >= 2
        assert any(artifact["format"] == "docx" for artifact in artifacts)
        assert any(artifact["format"] == "mbox" and artifact["message_count"] >= 6 for artifact in artifacts)
        for artifact in artifacts:
            artifact_path = output / artifact["path"]
            assert artifact_path.exists(), artifact_path
            if artifact.get("requires_ocr"):
                requires_ocr.append(artifact_path)
    for artifact in manifest["internal_knowledge"]["artifacts"]:
        artifact_path = output / artifact["path"]
        assert artifact_path.exists(), artifact_path

    assert len(requires_ocr) == 1
    assert _extract_pdf_text(requires_ocr[0]) == ""


def test_crm_csvs_parse_into_pydantic_models(tmp_path: Path) -> None:
    output = tmp_path / "synthetic"
    _run_generator(output)
    manifest = _load_manifest(output)

    for name, relative_path in manifest["crm"].items():
        model = CSV_MODELS[name]
        rows = _read_csv(output / relative_path)
        assert rows, name
        for row in rows:
            parsed = model.model_validate(_clean_row(row))
            assert parsed is not None


def test_generator_is_byte_identical_on_repeat(tmp_path: Path) -> None:
    output = tmp_path / "synthetic"
    _run_generator(output)
    first = _hash_tree(output)
    _run_generator(output)
    second = _hash_tree(output)
    assert second == first


def test_generated_content_uses_verified_fictional_names(tmp_path: Path) -> None:
    output = tmp_path / "synthetic"
    _run_generator(output)
    manifest_text = (output / "manifest.json").read_text(encoding="utf-8")

    assert "Brannfeld Industrial GmbH" in manifest_text
    assert "Rynvoss Logistics BV" in manifest_text
    assert "Caldrisa Dental Group" in manifest_text
    assert "Internal company knowledge" in manifest_text
    assert "SOC 2 readiness work is underway; certification is not claimed" in (
        output / "accounts" / "internal_company_knowledge" / "all_hands_strategy_recap.md"
    ).read_text(encoding="utf-8")


def _run_generator(output: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_synthetic.py",
            "--output",
            str(output),
            "--reference-date",
            REFERENCE_DATE,
            "--clean",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )


def _load_manifest(output: Path) -> dict[str, Any]:
    manifest_path = output / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest["accounts"], list)
    assert isinstance(manifest["crm"], dict)
    for account in manifest["accounts"]:
        assert {"account_id", "account_slug", "account_name", "artifacts"} <= set(account)
        assert isinstance(account["artifacts"], list)
    return manifest


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _clean_row(row: dict[str, str]) -> dict[str, Any]:
    return {key: (None if value == "" else value) for key, value in row.items()}


def _hash_tree(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        hashes[str(file_path.relative_to(path))] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return hashes


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "".join(page.extract_text() or "" for page in reader.pages).strip()
