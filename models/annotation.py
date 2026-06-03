"""Annotation data structures used by the PDF canvas and JSON store."""

from dataclasses import dataclass, field
from typing import Any


Point = tuple[float, float]


@dataclass
class Annotation:
    """One pen stroke drawn on a PDF page."""

    type: str = "pen"
    color: str = "#ff0000"
    width: int = 3
    points: list[Point] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the annotation to a JSON-friendly dictionary."""
        return {
            "type": self.type,
            "color": self.color,
            "width": self.width,
            "points": [[x, y] for x, y in self.points],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Annotation":
        """Create an annotation from JSON data."""
        raw_points = data.get("points", [])
        points: list[Point] = []

        for point in raw_points:
            if isinstance(point, (list, tuple)) and len(point) == 2:
                points.append((float(point[0]), float(point[1])))

        return cls(
            type=str(data.get("type", "pen")),
            color=str(data.get("color", "#ff0000")),
            width=int(data.get("width", 3)),
            points=points,
        )
