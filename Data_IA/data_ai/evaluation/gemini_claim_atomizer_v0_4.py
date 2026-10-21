"""Experimental Gemini Claim Atomizer v0.4.

v0.4 is the candidate atomizer developed after v0.1-v0.3
experiments on the development/calibration set.

Important methodological constraints:
- the holdout set must not be used to design this prompt;
- no factual-support decision is made here;
- no evidence chunks are provided;
- this module is not integrated into production;
- non-propositional inputs may be explicitly rejected rather
  than reconstructed by inventing missing context.
"""

from __future__ import annotations

import json
import os
import time
from typing import Literal

from google import genai
from pydantic import BaseModel, Field, model_validator


ReviewStatus = Literal[
    "valid_claim",
    "non_propositional",
]

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


class ClaimAtomV04(BaseModel):
    """One independently evaluable atom."""

    text: str = Field(
        min_length=1,
    )

    atom_type: AtomType


class ClaimAtomizationV04Result(BaseModel):
    """Validated result returned by Claim Atomizer v0.4."""

    source_claim_id: str

    review_status: ReviewStatus

    atomization_class: (
        AtomizationClass | None
    ) = None

    atoms: list[
        ClaimAtomV04
    ] = Field(
        default_factory=list,
    )

    model: str

    prompt_version: str

    latency_ms: int = Field(
        ge=0,
    )

    @model_validator(
        mode="after"
    )
    def validate_result(
        self,
    ) -> "ClaimAtomizationV04Result":
        if (
            self.review_status
            == "non_propositional"
        ):
            if (
                self.atomization_class
                is not None
            ):
                raise ValueError(
                    "non_propositional result "
                    "must not define "
                    "atomization_class"
                )

            if self.atoms:
                raise ValueError(
                    "non_propositional result "
                    "must not contain atoms"
                )

            return self

        if (
            self.atomization_class
            is None
        ):
            raise ValueError(
                "valid_claim result must "
                "define atomization_class"
            )

        if not self.atoms:
            raise ValueError(
                "valid_claim result must "
                "contain at least one atom"
            )

        if (
            self.atomization_class
            == "atomic"
            and len(self.atoms) != 1
        ):
            raise ValueError(
                "atomic result must "
                "contain exactly one atom"
            )

        if (
            self.atomization_class
            == "compound"
            and len(self.atoms) < 2
        ):
            raise ValueError(
                "compound result must "
                "contain at least two atoms"
            )

        return self


class _GeminiClaimAtomV04(
    BaseModel
):
    text: str = Field(
        min_length=1,
    )

    atom_type: AtomType


class _GeminiClaimAtomizationV04Payload(
    BaseModel
):
    """Schema requested directly from Gemini."""

    review_status: ReviewStatus

    atomization_class: (
        AtomizationClass | None
    ) = None

    atoms: list[
        _GeminiClaimAtomV04
    ] = Field(
        default_factory=list,
    )

    @model_validator(
        mode="after"
    )
    def validate_payload(
        self,
    ) -> (
        "_GeminiClaimAtomizationV04Payload"
    ):
        if (
            self.review_status
            == "non_propositional"
        ):
            if (
                self.atomization_class
                is not None
            ):
                raise ValueError(
                    "non_propositional "
                    "must use null "
                    "atomization_class"
                )

            if self.atoms:
                raise ValueError(
                    "non_propositional "
                    "must return zero atoms"
                )

            return self

        if (
            self.atomization_class
            is None
        ):
            raise ValueError(
                "valid_claim must define "
                "atomization_class"
            )

        if not self.atoms:
            raise ValueError(
                "valid_claim must return "
                "at least one atom"
            )

        if (
            self.atomization_class
            == "atomic"
            and len(self.atoms) != 1
        ):
            raise ValueError(
                "atomic must contain "
                "exactly one atom"
            )

        if (
            self.atomization_class
            == "compound"
            and len(self.atoms) < 2
        ):
            raise ValueError(
                "compound must contain "
                "at least two atoms"
            )

        return self


class ClaimAtomizerV04Error(
    RuntimeError
):
    """Base error for experimental v0.4."""


class ClaimAtomizerV04InvalidOutputError(
    ClaimAtomizerV04Error
):
    """Gemini returned unusable structured output."""


class GeminiClaimAtomizerV04:
    """Experimental Gemini-based Claim Atomizer v0.4."""

    PROMPT_VERSION = (
        "claim-atomizer-v0.4"
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: object | None = None,
    ) -> None:
        resolved_api_key = (
            api_key
            or os.getenv(
                "DATA_IA_GEMINI_API_KEY",
                "",
            )
        ).strip()

        resolved_model = (
            model
            or os.getenv(
                "DATA_IA_GEMINI_MODEL",
                "",
            )
        ).strip()

        if not resolved_api_key:
            raise ValueError(
                "DATA_IA_GEMINI_API_KEY "
                "is required."
            )

        if not resolved_model:
            raise ValueError(
                "DATA_IA_GEMINI_MODEL "
                "is required."
            )

        self._model = (
            resolved_model
        )

        if client is not None:
            self._client = client
        else:
            self._client = (
                genai.Client(
                    api_key=(
                        resolved_api_key
                    )
                )
            )

    @property
    def model(
        self,
    ) -> str:
        return self._model

    @property
    def prompt_version(
        self,
    ) -> str:
        return self.PROMPT_VERSION

    def atomize(
        self,
        *,
        source_claim_id: str,
        claim_text: str,
        format: str,
    ) -> ClaimAtomizationV04Result:
        clean_claim = (
            claim_text.strip()
        )

        if not clean_claim:
            raise ValueError(
                "claim_text must not "
                "be empty."
            )

        prompt = self._build_prompt(
            source_claim_id=(
                source_claim_id
            ),
            claim_text=clean_claim,
            format=format,
        )

        started_at = (
            time.perf_counter()
        )

        try:
            response = (
                self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config={
                        "temperature": 0,
                        "response_mime_type": (
                            "application/json"
                        ),
                        "response_schema": (
                            _GeminiClaimAtomizationV04Payload
                        ),
                    },
                )
            )

        except Exception as exc:
            raise ClaimAtomizerV04Error(
                "Gemini claim atomization "
                "request failed."
            ) from exc

        latency_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        payload = (
            self._parse_response(
                response
            )
        )

        return (
            ClaimAtomizationV04Result(
                source_claim_id=(
                    source_claim_id
                ),
                review_status=(
                    payload.review_status
                ),
                atomization_class=(
                    payload.atomization_class
                ),
                atoms=[
                    ClaimAtomV04(
                        text=atom.text,
                        atom_type=(
                            atom.atom_type
                        ),
                    )
                    for atom
                    in payload.atoms
                ],
                model=self._model,
                prompt_version=(
                    self.PROMPT_VERSION
                ),
                latency_ms=(
                    latency_ms
                ),
            )
        )

    @staticmethod
    def _parse_response(
        response: object,
    ) -> (
        _GeminiClaimAtomizationV04Payload
    ):
        parsed = getattr(
            response,
            "parsed",
            None,
        )

        if parsed is not None:
            try:
                if isinstance(
                    parsed,
                    _GeminiClaimAtomizationV04Payload,
                ):
                    return parsed

                return (
                    _GeminiClaimAtomizationV04Payload
                    .model_validate(
                        parsed
                    )
                )

            except Exception as exc:
                raise (
                    ClaimAtomizerV04InvalidOutputError(
                        "Gemini parsed output "
                        "does not match the "
                        "v0.4 schema."
                    )
                ) from exc

        text = getattr(
            response,
            "text",
            None,
        )

        if (
            not isinstance(
                text,
                str,
            )
            or not text.strip()
        ):
            raise (
                ClaimAtomizerV04InvalidOutputError(
                    "Gemini returned an "
                    "empty response."
                )
            )

        try:
            raw = json.loads(
                text
            )

            return (
                _GeminiClaimAtomizationV04Payload
                .model_validate(
                    raw
                )
            )

        except Exception as exc:
            raise (
                ClaimAtomizerV04InvalidOutputError(
                    "Gemini response could "
                    "not be validated as "
                    "Claim Atomization v0.4."
                )
            ) from exc

    @classmethod
    def _build_prompt(
        cls,
        *,
        source_claim_id: str,
        claim_text: str,
        format: str,
    ) -> str:
        return f"""
You are a CLAIM ATOMIZER for an educational
content quality-evaluation system.

PROMPT VERSION:
{cls.PROMPT_VERSION}

Your job is ONLY to determine whether the supplied
text contains an evaluable proposition and, when it
does, split it into the MINIMUM number of
independently evaluable factual atoms.

You are NOT evaluating whether the claim is true.
You are NOT checking evidence.
You are NOT correcting the text.
You are NOT using external knowledge.
You are NOT deciding factual support.

INPUT METADATA

source_claim_id:
{source_claim_id}

content_format:
{format}

source_claim:
{claim_text}


==================================================
STEP 1 — PROPOSITIONAL VALIDITY
==================================================

First determine whether the input actually expresses
at least one factual proposition.

Use:

review_status = "valid_claim"

when the text contains at least one proposition that
can meaningfully be evaluated for factual support.

Use:

review_status = "non_propositional"

when the input is only a term, title, keyword,
nominal list, sentence fragment, or other text that
does not provide enough explicit information to form
a factual proposition.

IMPORTANT:

Do NOT invent a missing subject.

Do NOT invent a missing predicate.

Do NOT invent an object.

Do NOT resolve an omitted context by guessing.

Do NOT transform a keyword or heading into a factual
statement.

A fragment remains a fragment.

If review_status is "non_propositional":

atomization_class MUST be null.
atoms MUST be [].


==================================================
STEP 2 — MINIMAL ATOMIZATION
==================================================

If review_status = "valid_claim", identify the
MINIMUM number of independently evaluable
propositions or relations.

Use:

atomic
    One independently evaluable proposition.

compound
    Two or more independently evaluable factual
    propositions.

relational
    The claim contains an explicit temporal, causal,
    conditional, comparative, scope, negation, or
    other relation whose isolation is necessary for
    factual evaluation.

A relational claim may contain ONE atom if the
relation itself is the indivisible factual unit.


==================================================
CORE RULES
==================================================

1. MINIMUM NECESSARY SPLITTING

Do not split merely because a sentence is long.

Do not split merely because punctuation appears.

Do not split merely because a conjunction appears.

Create another atom only when the resulting
proposition could reasonably receive a different
factual-support judgment.


2. KEEP QUALIFIERS WITH THEIR PROPOSITION

Words expressing:

- automatically
- always
- never
- all
- only
- by default
- generally
- approximately
- possible
- required
- optional
- recommended

and similar qualifiers belong to the proposition
they modify.

Do not create a separate atom solely for a
qualifier.


3. SHARED-PREDICATE LISTS

A list sharing one predicate normally stays in one
atom.

Synthetic example:

"The lesson covers matrices, vectors and tensors."

Correct:
ONE factual proposition.

Do NOT create one atom for matrices, one for
vectors, and one for tensors unless the source
asserts independent predicates about them.


4. INDEPENDENT PREDICATES

Split propositions when different predicates express
facts that could be independently supported.

Synthetic example:

"The service stores documents and the worker sends
notifications."

Correct:
TWO factual propositions.


5. GENERAL STATEMENT PLUS INDEPENDENT DETAILS

A general statement and its details may be separated
ONLY when the details themselves assert independently
evaluable facts.

Synthetic example:

"The module teaches data processing, including
reading files and validating schemas."

Possible decomposition:

- The module teaches data processing.
- The module teaches reading files.
- The module teaches validating schemas.

But do NOT mechanically split every list introduced
by words such as "including".


6. RELATIVE OR PARTICIPIAL CLAUSES

A relative or participial clause may encode another
independent proposition.

Split it only when it contributes a distinct factual
assertion.

Do not split descriptive wording that merely
qualifies the same fact.


7. RELATIONS

When temporal, causal, conditional or comparative
information can receive a different support judgment,
isolate the relation.

Examples of relation types:

temporal_relation
causal_relation
conditional_relation
comparative_relation

However, do NOT contaminate base propositions with
relational language.

Synthetic example:

"First the system loads the configuration; later it
starts the worker."

Possible atoms:

- The system loads the configuration.
- The system starts the worker.
- Loading the configuration occurs before starting
  the worker.

The base propositions must remain free of "first",
"later", "before", "after", etc. when those words are
represented by a separate relation atom.


8. CAUSAL LANGUAGE

Do NOT label a proposition causal merely because it
contains a verb such as:

improves
enables
allows
supports
reduces
increases

Use causal_relation only when the claim actually
asserts an explicit causal or explanatory relation
that should be evaluated as such.


9. NEGATION

A negative proposition can remain one atom.

Use negation_or_absence when the factual content is
specifically the absence, prohibition, lack,
non-requirement, or negation of something.

Do not create a positive atom plus a negative atom
when the source contains only the negative claim.


10. SCOPE AND QUANTIFIERS

Quantifiers normally remain attached to their
proposition.

Use scope_or_quantifier as a separate atom only when
the scope itself is an independently asserted factual
relation.

For example, "all", "every", "only", or "none" does
NOT automatically create another atom.


11. INDEPENDENT EVALUABILITY

Every atom must:

- preserve the source meaning;
- contain enough explicit information to be
  evaluated;
- avoid invented context;
- avoid references introduced by the atomizer;
- avoid unnecessary redundancy.


12. NO REDUNDANCY

Do not create two atoms that express essentially the
same proposition.

Do not produce:

- a general restatement,
- plus a synonym,
- plus the same claim with a qualifier separated.

Each atom must add independently evaluable factual
content.


==================================================
ATOM TYPES
==================================================

Use exactly one of:

factual_proposition
temporal_relation
causal_relation
conditional_relation
comparative_relation
negation_or_absence
scope_or_quantifier


==================================================
DECISION TEST
==================================================

Before creating an additional atom, ask:

"Could one of these propositions be supported by the
evidence while the other is unsupported?"

If NO:
keep them together.

If YES:
they may need separate atoms.

But this test does NOT override the qualifier rule.

A qualifier is not automatically a separate
proposition.


==================================================
OUTPUT
==================================================

Return ONLY the structured JSON requested by the
schema.

Do not explain your reasoning.

Do not add markdown.

Do not add evidence.

Do not add factual-support labels.
""".strip()