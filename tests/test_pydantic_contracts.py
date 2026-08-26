from __future__ import annotations

import pytest

pydantic = pytest.importorskip("pydantic")
from pydantic import BaseModel, Field, ValidationError, field_validator

from pulsarlab.core.types import GlitchComponent, ParModel


class GlitchContract(BaseModel):
    index: int = Field(ge=1)
    glep: float | None = None
    gltd: float | None = None

    @field_validator("gltd")
    @classmethod
    def gltd_positive_or_none(cls, value):
        if value is not None and value <= 0:
            raise ValueError("GLTD must be positive when present")
        return value


class ParContract(BaseModel):
    f0: float = Field(gt=0)
    pepoch: float


def test_pydantic_contract_accepts_valid_core_objects():
    model = ParModel(params={"F0": 11.0, "PEPOCH": 58000.0}, glitches=(GlitchComponent(index=1, glep=58001, gltd=5),))
    ParContract(f0=model.f0, pepoch=model.pepoch)
    GlitchContract(index=model.glitches[0].index, glep=model.glitches[0].glep, gltd=model.glitches[0].gltd)


def test_pydantic_contract_rejects_unphysical_values():
    with pytest.raises(ValidationError):
        ParContract(f0=-1.0, pepoch=58000.0)
    with pytest.raises(ValidationError):
        GlitchContract(index=1, glep=58000.0, gltd=0.0)
