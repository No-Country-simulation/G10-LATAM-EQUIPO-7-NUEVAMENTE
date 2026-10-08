"""Metadatos pedagógicos asociados a la adaptación de un documento."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LearningMetadata:
    """Metadatos de aprendizaje generados una vez por adaptación.

    Los metadatos pertenecen al documento/adaptación y no a un formato
    pedagógico individual. Por ello se mantienen fuera de Quiz,
    Flashcards u otros contenidos generados.

    Attributes:
        key_concepts: Conceptos o ideas principales identificadas.
        prerequisites: Conocimientos previos recomendados.
        estimated_time_minutes: Tiempo estimado de estudio en minutos.
    """

    key_concepts: tuple[str, ...]
    prerequisites: tuple[str, ...]
    estimated_time_minutes: int

    def __post_init__(self) -> None:
        """Valida las invariantes del contrato interno."""
        self._validate_text_items(
            self.key_concepts,
            field_name="key_concepts",
        )
        self._validate_text_items(
            self.prerequisites,
            field_name="prerequisites",
        )

        if (
            isinstance(
                self.estimated_time_minutes,
                bool,
            )
            or not isinstance(
                self.estimated_time_minutes,
                int,
            )
            or self.estimated_time_minutes < 0
        ):
            raise ValueError(
                "estimated_time_minutes debe ser "
                "un entero mayor o igual a cero."
            )

    @classmethod
    def empty(cls) -> "LearningMetadata":
        """Construye el fallback oficial cuando no hay metadata útil."""
        return cls(
            key_concepts=(),
            prerequisites=(),
            estimated_time_minutes=0,
        )

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, object],
    ) -> "LearningMetadata":
        """Construye el contrato desde una representación serializada."""
        key_concepts = cls._parse_text_items(
            data.get("key_concepts"),
            field_name="key_concepts",
        )
        prerequisites = cls._parse_text_items(
            data.get("prerequisites"),
            field_name="prerequisites",
        )

        estimated_time_minutes = data.get(
            "estimated_time_minutes"
        )

        if (
            isinstance(
                estimated_time_minutes,
                bool,
            )
            or not isinstance(
                estimated_time_minutes,
                int,
            )
        ):
            raise ValueError(
                "estimated_time_minutes debe ser un entero."
            )

        return cls(
            key_concepts=key_concepts,
            prerequisites=prerequisites,
            estimated_time_minutes=(
                estimated_time_minutes
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Serializa los metadatos a una estructura JSON-compatible."""
        return {
            "key_concepts": list(
                self.key_concepts
            ),
            "prerequisites": list(
                self.prerequisites
            ),
            "estimated_time_minutes": (
                self.estimated_time_minutes
            ),
        }

    @staticmethod
    def _parse_text_items(
        value: object,
        *,
        field_name: str,
    ) -> tuple[str, ...]:
        """Normaliza una lista serializada de textos a una tupla."""
        if not isinstance(
            value,
            list,
        ):
            raise ValueError(
                f"{field_name} debe ser una lista."
            )

        items = tuple(
            value
        )

        LearningMetadata._validate_text_items(
            items,
            field_name=field_name,
        )

        return items

    @staticmethod
    def _validate_text_items(
        items: tuple[str, ...],
        *,
        field_name: str,
    ) -> None:
        """Valida que una colección contenga únicamente textos útiles."""
        for index, item in enumerate(
            items
        ):
            if (
                not isinstance(
                    item,
                    str,
                )
                or not item.strip()
            ):
                raise ValueError(
                    f"{field_name}[{index}] "
                    "debe ser un texto no vacío."
                )