"""Event envelope contract tests (T-02)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from cim.common.chain import compute_record_hash
from cim.common.schema import SCHEMA_VERSION
from cim.common.schema.canonical import canonical_json
from cim.common.schema.envelope import Artefact, Event

BEHAVIOUR: dict[str, Any] = {
    "skill_id": "pdf-tools",
    "invocation_id": "inv-0001",
    "cgroup_id": "cim-skill-pdf-tools-inv-0001.scope",
    "binaries_executed": ["/usr/bin/python3"],
    "file_write_targets": ["/tmp"],
    "egress": [{"dest_class": "private_ip", "port": 8080}],
    "process_count": 2,
    "duration_us": 1250000,
}
TS = "2026-10-19T10:00:00Z"


def skill_event(payload: dict[str, Any], skill: str = "pdf-tools") -> Event:
    return Event(
        ts=TS,
        artefact=Artefact(type="skill", skill=skill),
        kind="behaviour",
        payload=payload,
    )


def test_round_trip() -> None:
    event = skill_event(BEHAVIOUR)
    assert Event.model_validate_json(event.model_dump_json()) == event


def test_schema_version_matches_constant() -> None:
    assert skill_event(BEHAVIOUR).schema_version == SCHEMA_VERSION


def test_bad_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        Event(
            ts="yesterday",
            artefact=Artefact(type="skill", skill="pdf-tools"),
            kind="behaviour",
            payload=BEHAVIOUR,
        )


def test_float_rejected_in_any_payload() -> None:
    with pytest.raises(ValidationError):
        Event(
            ts=TS,
            artefact=Artefact(type="mcp_tool", server="hexstrike", tool="nmap_scan"),
            kind="behaviour",
            payload={"result_bytes": 1.5},
        )


def test_skill_payload_is_validated() -> None:
    with pytest.raises(ValidationError):
        skill_event({"skill_id": "pdf-tools"})


def test_skill_id_must_match_artefact() -> None:
    with pytest.raises(ValidationError):
        skill_event(BEHAVIOUR, skill="other-skill")


def test_artefact_requires_identifiers() -> None:
    with pytest.raises(ValidationError):
        Artefact(type="mcp_tool", server="hexstrike")


def test_hash_independent_of_key_order() -> None:
    reordered = dict(reversed(list(BEHAVIOUR.items())))
    a = compute_record_hash("0" * 64, "behaviour", canonical_json(BEHAVIOUR))
    b = compute_record_hash("0" * 64, "behaviour", skill_event(reordered).payload_canonical())
    assert a == b
