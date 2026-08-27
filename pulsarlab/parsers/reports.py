"""Parser and validation report classes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Report:
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, other: "Report") -> None:
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)


@dataclass
class ParParseReport(Report):
    lines_read: int = 0
    lines_used: int = 0
    skipped_lines: int = 0
    invalid_parameters: int = 0
    incomplete_glitches: int = 0
    glitches_found: int = 0


@dataclass
class DatParseReport(Report):
    lines_read: int = 0
    lines_used: int = 0
    skipped_lines: int = 0
    scaled_f1: bool = False
    scaled_f2: bool = False


@dataclass
class TimParseReport(Report):
    lines_read: int = 0
    lines_used: int = 0
    skipped_lines: int = 0
    directives_seen: int = 0
    invalid_toas: int = 0
    format_name: str = "TEMPO2 FORMAT 1"
