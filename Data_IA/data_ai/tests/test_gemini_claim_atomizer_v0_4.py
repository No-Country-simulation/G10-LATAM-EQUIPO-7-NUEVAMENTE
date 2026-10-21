"""Tests for experimental Gemini Claim Atomizer v0.4."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from data_ai.evaluation.gemini_claim_atomizer_v0_4 import (
    ClaimAtomizationV04Result,
    ClaimAtomizerV04InvalidOutputError,
    GeminiClaimAtomizerV04,
)


class FakeModels:
    def __init__(
        self,
        response_text: str,
    ) -> None:
        self.response_text = (
            response_text
        )

        self.calls = []

    def generate_content(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        return SimpleNamespace(
            text=self.response_text,
            parsed=None,
        )


class FakeClient:
    def __init__(
        self,
        response_text: str,
    ) -> None:
        self.models = FakeModels(
            response_text
        )


def make_provider(
    payload: dict,
) -> GeminiClaimAtomizerV04:
    return GeminiClaimAtomizerV04(
        api_key="test-api-key",
        model="test-model",
        client=FakeClient(
            json.dumps(
                payload
            )
        ),
    )


def test_requires_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "DATA_IA_GEMINI_API_KEY",
        raising=False,
    )

    monkeypatch.setenv(
        "DATA_IA_GEMINI_MODEL",
        "test-model",
    )

    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_API_KEY",
    ):
        GeminiClaimAtomizerV04()


def test_requires_model(
    monkeypatch,
):
    monkeypatch.setenv(
        "DATA_IA_GEMINI_API_KEY",
        "test-api-key",
    )

    monkeypatch.delenv(
        "DATA_IA_GEMINI_MODEL",
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="DATA_IA_GEMINI_MODEL",
    ):
        GeminiClaimAtomizerV04()


def test_prompt_version():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "atomic"
            ),
            "atoms": [
                {
                    "text": (
                        "El sistema "
                        "procesa datos."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    assert (
        provider.prompt_version
        == "claim-atomizer-v0.4"
    )


def test_exposes_model():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "atomic"
            ),
            "atoms": [
                {
                    "text": (
                        "El sistema "
                        "procesa datos."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    assert (
        provider.model
        == "test-model"
    )


def test_accepts_non_propositional_term():
    provider = make_provider(
        {
            "review_status": (
                "non_propositional"
            ),
            "atomization_class": None,
            "atoms": [],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-001"
        ),
        claim_text=(
            "Arquitectura."
        ),
        format="tldr",
    )

    assert isinstance(
        result,
        ClaimAtomizationV04Result,
    )

    assert (
        result.review_status
        == "non_propositional"
    )

    assert (
        result.atomization_class
        is None
    )

    assert result.atoms == []


def test_accepts_non_propositional_nominal_list():
    provider = make_provider(
        {
            "review_status": (
                "non_propositional"
            ),
            "atomization_class": None,
            "atoms": [],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-002"
        ),
        claim_text=(
            "Matrices, vectores "
            "y tensores."
        ),
        format="flashcards",
    )

    assert (
        result.review_status
        == "non_propositional"
    )

    assert not result.atoms


def test_accepts_simple_atomic_claim():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "atomic"
            ),
            "atoms": [
                {
                    "text": (
                        "El servicio "
                        "almacena archivos."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-003"
        ),
        claim_text=(
            "El servicio "
            "almacena archivos."
        ),
        format="quiz",
    )

    assert (
        result.review_status
        == "valid_claim"
    )

    assert (
        result.atomization_class
        == "atomic"
    )

    assert len(
        result.atoms
    ) == 1

    assert (
        result.atoms[0].atom_type
        == "factual_proposition"
    )


def test_qualifier_stays_inside_atomic_claim():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "atomic"
            ),
            "atoms": [
                {
                    "text": (
                        "El proceso valida "
                        "automáticamente "
                        "todos los registros."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-004"
        ),
        claim_text=(
            "El proceso valida "
            "automáticamente todos "
            "los registros."
        ),
        format="tldr",
    )

    assert len(
        result.atoms
    ) == 1

    assert (
        "automáticamente"
        in result.atoms[0].text
    )

    assert (
        "todos"
        in result.atoms[0].text
    )


def test_accepts_two_independent_predicates():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "compound"
            ),
            "atoms": [
                {
                    "text": (
                        "El servicio "
                        "almacena documentos."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                },
                {
                    "text": (
                        "El worker "
                        "envía notificaciones."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                },
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-005"
        ),
        claim_text=(
            "El servicio almacena "
            "documentos y el worker "
            "envía notificaciones."
        ),
        format="video_script",
    )

    assert (
        result.atomization_class
        == "compound"
    )

    assert len(
        result.atoms
    ) == 2


def test_shared_predicate_list_can_remain_atomic():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "atomic"
            ),
            "atoms": [
                {
                    "text": (
                        "La lección cubre "
                        "matrices, vectores "
                        "y tensores."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-006"
        ),
        claim_text=(
            "La lección cubre matrices, "
            "vectores y tensores."
        ),
        format="flashcards",
    )

    assert (
        result.atomization_class
        == "atomic"
    )

    assert len(
        result.atoms
    ) == 1


def test_accepts_relational_output():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "relational"
            ),
            "atoms": [
                {
                    "text": (
                        "El sistema carga "
                        "la configuración."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                },
                {
                    "text": (
                        "El sistema inicia "
                        "el worker."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                },
                {
                    "text": (
                        "La carga de la "
                        "configuración ocurre "
                        "antes del inicio "
                        "del worker."
                    ),
                    "atom_type": (
                        "temporal_relation"
                    ),
                },
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-007"
        ),
        claim_text=(
            "Primero el sistema carga "
            "la configuración y después "
            "inicia el worker."
        ),
        format="video_script",
    )

    assert (
        result.atomization_class
        == "relational"
    )

    assert len(
        result.atoms
    ) == 3

    assert (
        result.atoms[2].atom_type
        == "temporal_relation"
    )


def test_accepts_single_atom_relational_output():
    provider = make_provider(
        {
            "review_status": (
                "valid_claim"
            ),
            "atomization_class": (
                "relational"
            ),
            "atoms": [
                {
                    "text": (
                        "La operación B "
                        "ocurre después "
                        "de la operación A."
                    ),
                    "atom_type": (
                        "temporal_relation"
                    ),
                }
            ],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-008"
        ),
        claim_text=(
            "La operación B ocurre "
            "después de la operación A."
        ),
        format="tldr",
    )

    assert (
        result.atomization_class
        == "relational"
    )

    assert len(
        result.atoms
    ) == 1

    assert (
        result.atoms[0].atom_type
        == "temporal_relation"
    )


def test_fragment_is_not_reconstructed():
    provider = make_provider(
        {
            "review_status": (
                "non_propositional"
            ),
            "atomization_class": None,
            "atoms": [],
        }
    )

    result = provider.atomize(
        source_claim_id=(
            "SYNTH-009"
        ),
        claim_text=(
            "Como plataforma "
            "distribuida."
        ),
        format="flashcards",
    )

    assert (
        result.review_status
        == "non_propositional"
    )

    assert (
        result.atomization_class
        is None
    )

    assert result.atoms == []


def test_rejects_empty_response():
    provider = GeminiClaimAtomizerV04(
        api_key="test-api-key",
        model="test-model",
        client=FakeClient(""),
    )

    with pytest.raises(
        ClaimAtomizerV04InvalidOutputError,
    ):
        provider.atomize(
            source_claim_id=(
                "SYNTH-010"
            ),
            claim_text=(
                "El servicio "
                "procesa eventos."
            ),
            format="quiz",
        )


def test_rejects_atoms_for_non_propositional():
    provider = make_provider(
        {
            "review_status": (
                "non_propositional"
            ),
            "atomization_class": None,
            "atoms": [
                {
                    "text": (
                        "La arquitectura "
                        "existe."
                    ),
                    "atom_type": (
                        "factual_proposition"
                    ),
                }
            ],
        }
    )

    with pytest.raises(
        ClaimAtomizerV04InvalidOutputError,
    ):
        provider.atomize(
            source_claim_id=(
                "SYNTH-011"
            ),
            claim_text=(
                "Arquitectura."
            ),
            format="tldr",
        )