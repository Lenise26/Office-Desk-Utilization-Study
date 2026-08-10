from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ObservationCreate(BaseModel):
    desk_id: int = Field(gt=0)
    observed_at: datetime
    occupied: bool
    approximate_duration_minutes: int | None = Field(default=None, ge=0, le=480)

    @model_validator(mode="after")
    def duration_matches_status(self) -> "ObservationCreate":
        if not self.occupied and self.approximate_duration_minutes not in (None, 0):
            raise ValueError("Duration must be empty or zero when a desk is unoccupied.")
        return self


class DashboardQuery(BaseModel):
    layout_id: int = Field(gt=0)
    period: Literal["all", "morning", "midday", "afternoon", "late"] = "all"


class ComparisonQuery(BaseModel):
    before_layout_id: int = Field(gt=0)
    after_layout_id: int = Field(gt=0)

    @field_validator("after_layout_id")
    @classmethod
    def different_layouts(cls, value: int, info):
        if info.data.get("before_layout_id") == value:
            raise ValueError("Choose two different layouts for comparison.")
        return value
