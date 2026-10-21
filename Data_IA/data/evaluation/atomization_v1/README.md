# Claim Atomization Dataset v1

## Status

Frozen ground truth for experimental Claim Atomization v1.

This dataset is not part of the production `/evaluate/v2` pipeline.

## Purpose

Evaluate whether an automatic claim atomizer can decompose factual source
claims into minimal independently evaluable propositions while preserving:

- factual meaning;
- qualifiers;
- temporal relations;
- negations;
- scope;
- traceability to the original claim.

## Dataset

Source claims: 16

- supported source claims: 8
- unsupported source claims: 8

Formats represented:

- quiz
- flashcards
- tldr
- video_script

## Ground truth

Total expected atoms: 26

Atomization classes:

- atomic: 8
- compound: 5
- relational: 3

Expected atom support:

- supported: 17
- unsupported: 8
- uncertain: 1

## Evidence rule

`chunks_used` is the only valid factual evidence when assigning
`expected_support`.

Atomization itself must not use `chunks_used` to invent or rewrite claims.
It only decomposes information already present in the source claim.

## Important ambiguous case

`ATOM-V1-011` intentionally contains one `uncertain` atom.

The source claim states that `FastAPI` is a class, while the available
`chunks_used` demonstrate:

```python
from fastapi import FastAPI
```

but do not explicitly establish the symbol type.

This ambiguity was discovered during manual annotation before testing an
automatic atomizer and is therefore retained in the frozen ground truth.

## Files

- `atomization_dataset_v1.csv`
  - source claims selected for the experiment.

- `atomization_review_packet_v1.md`
  - source claims and evidence used during manual review.

- `atomization_ground_truth_v1.csv`
  - frozen expected atomization.

## Evaluation policy

Automatic atomizer outputs must be compared against the frozen ground truth.

The ground truth must not be modified after observing model outputs unless a
separate adjudication/versioning process is created.

Any future corrections must create a new dataset version rather than silently
overwriting v1.

## Production status

```text
claim_atomization_v1 = experimental
production_integration = false
```

No changes to `/evaluate/v2`, `SemanticEvaluator`, or the production
`content_support` decision layer are implied by this dataset.