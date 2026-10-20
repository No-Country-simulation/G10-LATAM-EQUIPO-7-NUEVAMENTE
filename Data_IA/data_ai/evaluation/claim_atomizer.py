"""Experimental Claim Atomizer v0.1.

This module decomposes a factual source claim into minimal,
independently evaluable factual atoms.

IMPORTANT:
- it does not evaluate factual support;
- it does not consume chunks_used;
- it is not integrated into /evaluate/v2;
- it is experimental.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field


AtomizationClass = Literal[
    "atomic",
    "compound",
    "relational",
]


AtomType = Literal[
    "factual_proposition",
    "temporal_relation",
    "causal_relation",
    "conditional_relation",
    "comparative_relation",
    "negation_or_absence",
    "scope_or_quantifier",
]


class GeneratedAtom(BaseModel):
    text: str = Field(
        min_length=1,
    )

    atom_type: AtomType


class ClaimAtomizationOutput(BaseModel):
    atomization_class: AtomizationClass

    atoms: list[GeneratedAtom] = Field(
        min_length=1,
        max_length=8,
    )


class ClaimAtomizationProvider(
    Protocol
):
    def atomize(
        self,
        *,
        source_claim_id: str,
        claim_text: str,
        format: str,
    ) -> ClaimAtomizationOutput:
        ...


class ClaimAtomizationResult(BaseModel):
    source_claim_id: str
    source_claim_text: str

    status: Literal[
        "success",
        "failed",
    ]

    atomization_class: (
        AtomizationClass
        | None
    ) = None

    atoms: list[
        GeneratedAtom
    ] = Field(
        default_factory=list,
    )

    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None

    error_code: str | None = None
    error_message: str | None = None


class ClaimAtomizer:
    """Thin orchestration layer for claim atomization."""

    def __init__(
        self,
        provider: ClaimAtomizationProvider,
    ) -> None:
        self._provider = provider

    def atomize(
        self,
        *,
        source_claim_id: str,
        claim_text: str,
        format: str,
    ) -> ClaimAtomizationResult:
        try:
            output = (
                self._provider.atomize(
                    source_claim_id=(
                        source_claim_id
                    ),
                    claim_text=(
                        claim_text
                    ),
                    format=format,
                )
            )

            return ClaimAtomizationResult(
                source_claim_id=(
                    source_claim_id
                ),
                source_claim_text=(
                    claim_text
                ),
                status="success",
                atomization_class=(
                    output.atomization_class
                ),
                atoms=output.atoms,
            )

        except Exception as exc:
            return ClaimAtomizationResult(
                source_claim_id=(
                    source_claim_id
                ),
                source_claim_text=(
                    claim_text
                ),
                status="failed",
                error_code=(
                    "atomization_error"
                ),
                error_message=str(exc),
            )