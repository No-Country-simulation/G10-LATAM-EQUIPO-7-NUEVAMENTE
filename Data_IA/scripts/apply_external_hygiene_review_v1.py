from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_review_pool_hygiene_v1.csv"
)

EXCLUDE = {
    "EXT-REV-V1-008",
    "EXT-REV-V1-019",
    "EXT-REV-V1-022",
    "EXT-REV-V1-081",
    "EXT-REV-V1-082",
    "EXT-REV-V1-083",
    "EXT-REV-V1-085",
    "EXT-REV-V1-086",
    "EXT-REV-V1-088",
    "EXT-REV-V1-105",
}

CLEAN = {
    "EXT-REV-V1-025": (
        "Configura el entrypoint de la app en pyproject.toml"
    ),
    "EXT-REV-V1-028": (
        'Paso 2: crea una "instance" de FastAPI'
    ),
    "EXT-REV-V1-033": (
        "Validación de datos"
    ),
}


def main() -> None:
    df = pd.read_csv(PATH)

    if "cleaned_claim_text" not in df.columns:
        df["cleaned_claim_text"] = df["claim_text"]

    # The automatic screen accepted all non-suspicious candidates.
    df["hygiene_status"] = "keep"
    df["hygiene_notes"] = (
        "passed_hygiene_screen"
    )

    for review_id in EXCLUDE:
        mask = df["review_id"] == review_id
        df.loc[mask, "hygiene_status"] = "exclude_noise"
        df.loc[mask, "hygiene_notes"] = (
            "manual_hygiene_adjudication"
        )

    for review_id, cleaned_text in CLEAN.items():
        mask = df["review_id"] == review_id

        df.loc[mask, "hygiene_status"] = "keep_cleaned"
        df.loc[mask, "cleaned_claim_text"] = cleaned_text
        df.loc[mask, "hygiene_notes"] = (
            "removed_navigation_anchor_marker"
        )

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("External hygiene adjudication v1")
    print("================================")
    print(df["hygiene_status"].value_counts().to_string())
    print()
    print(
        "Valid cases:",
        int(
            df["hygiene_status"]
            .isin(["keep", "keep_cleaned"])
            .sum()
        ),
    )
    print(
        "Excluded noise:",
        int(
            (df["hygiene_status"] == "exclude_noise").sum()
        ),
    )


if __name__ == "__main__":
    main()