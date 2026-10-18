"""Event envelope shared by both collectors and the store (T-02)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cim.common.schema.canonical import canonical_json
from cim.common.schema.skills import (
    SkillArtefactPayload,
    SkillBehaviourPayload,
    SkillIntegrityPayload,
)

Kind = Literal["artefact", "integrity", "behaviour", "alert"]

_SKILL_PAYLOADS: dict[str, type[BaseModel]] = {
    "artefact": SkillArtefactPayload,
    "integrity": SkillIntegrityPayload,
    "behaviour": SkillBehaviourPayload,
}

_REQUIRED_IDS: dict[str, tuple[str, ...]] = {
    "skill": ("skill",),
    "mcp_server": ("server",),
    "mcp_tool": ("server", "tool"),
}


class Artefact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["mcp_server", "mcp_tool", "skill"]
    server: str | None = None
    tool: str | None = None
    skill: str | None = None

    @model_validator(mode="after")
    def _check_ids(self) -> Self:
        missing = [f for f in _REQUIRED_IDS[self.type] if getattr(self, f) is None]
        if missing:
            raise ValueError(f"artefact type {self.type!r} requires: {', '.join(missing)}")
        return self


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    ts: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    artefact: Artefact
    kind: Kind
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _check_payload(self) -> Self:
        canonical_json(self.payload)  # rejects floats and non-JSON types
        if self.artefact.type == "skill" and self.kind in _SKILL_PAYLOADS:
            _SKILL_PAYLOADS[self.kind].model_validate(self.payload)
            if self.payload.get("skill_id") != self.artefact.skill:
                raise ValueError("payload skill_id does not match artefact.skill")
        return self

    def payload_canonical(self) -> str:
        return canonical_json(self.payload)
