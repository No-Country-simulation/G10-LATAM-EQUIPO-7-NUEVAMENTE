"""Tipos compartidos para el contexto de adaptación educativa."""

from typing import Annotated, Literal

from pydantic import StringConstraints

NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

AdaptationProfile = Literal[
    "beginner",
    "intermediate",
    "advanced",
]

AdaptationNiche = Literal[
    "general",
    "backend",
    "health",
    "legal",
    "business",
    "humanities",
]