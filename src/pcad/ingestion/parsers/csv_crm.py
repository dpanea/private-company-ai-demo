from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from pcad.models import Account, SyntheticDataset, UserOwner


ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_crm_manifest_csvs(synthetic_dir: Path, paths: dict[str, str]) -> SyntheticDataset:
    """Load owners and accounts CSVs from manifest-relative paths."""
    return SyntheticDataset(
        users=_load_csv(synthetic_dir / paths["users"], UserOwner),
        accounts=_load_csv(synthetic_dir / paths["accounts"], Account),
    )


def _load_csv(path: Path, model: type[ModelT]) -> list[ModelT]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        _validate_header(path, model, reader.fieldnames)
        rows: list[ModelT] = []
        for line_number, row in enumerate(reader, start=2):
            cleaned = {key: _empty_to_none(value) for key, value in row.items()}
            try:
                rows.append(model.model_validate(cleaned))
            except ValidationError as exc:
                raise ValueError(f"{path}:{line_number} does not match {model.__name__}: {exc}") from exc
    return rows


def _validate_header(path: Path, model: type[BaseModel], fieldnames: list[str]) -> None:
    expected = set(model.model_fields)
    actual = set(fieldnames)
    missing = sorted(name for name in expected - actual if model.model_fields[name].is_required())
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{path} header mismatch for {model.__name__}: missing required={missing}, unknown={unknown}"
        )


def _empty_to_none(value: Any) -> Any:
    if value == "":
        return None
    return value
