"""Canonical JSON interchange format for field jobs.

A ``.sfield.json`` job file is the contract between survey-field and every
downstream consumer (adjustment workflow, COGO drafting, desktop app):

.. code-block:: json

    {
      "format": "survey-field/job",
      "schema_version": 1,
      "generator": "survey-field 0.1.0",
      "project": { ... Project.to_dict() ... }
    }

Schema changes bump ``schema_version``; readers reject newer versions they do
not understand (fail loud, never misread coordinates).
"""

from __future__ import annotations

import json
from typing import Any, Dict

from . import __version__
from .models import JOB_FORMAT, SCHEMA_VERSION, Project


def dump_job(project: Project) -> Dict[str, Any]:
    return {
        "format": JOB_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "generator": f"survey-field {__version__}",
        "project": project.to_dict(),
    }


def load_job(data: Dict[str, Any]) -> Project:
    if data.get("format") != JOB_FORMAT:
        raise ValueError(
            f"not a survey-field job file (format={data.get('format')!r})")
    version = data.get("schema_version", 0)
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"job schema v{version} is newer than this reader (v{SCHEMA_VERSION}); "
            "upgrade survey-field")
    return Project.from_dict(data["project"])


def write_job(project: Project, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dump_job(project), fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def read_job(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as fh:
        return load_job(json.load(fh))
