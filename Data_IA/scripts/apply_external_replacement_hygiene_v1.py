from pathlib import Path

import pandas as pd


PATH = Path(
    "data/evaluation/atomization_external_v1/"
    "dataset/external_claim_hygiene_replacements_v1.csv"
)

EXCLUDE = {
    "EXT-REPL-V1-007",
}

CLEAN = {
    "EXT-REPL-V1-008": (
        "Compute the skew of the values in each group"
    ),
    "EXT-REPL-V1-010": (
        "Cuando los usuarios con discapacidad visual usan un "
        "lector de pantalla para leer el contenido de una página "
        "web e interactuar con él, el lector de pantalla lee en "
        "voz alta el texto de la etiqueta asociada al llegar a "
        "cada control."
    ),
}


def main() -> None:
    df = pd.read_csv(PATH)

    if "cleaned_claim_text" not in df.columns:
        df["cleaned_claim_text"] = df["claim_text"]

    df["hygiene_status"] = "keep"
    df["hygiene_notes"] = "manual_hygiene_adjudication"

    for replacement_id in EXCLUDE:
        mask = df["replacement_id"] == replacement_id

        df.loc[mask, "hygiene_status"] = "exclude_noise"
        df.loc[mask, "hygiene_notes"] = (
            "example_output_not_documentary_content"
        )

    for replacement_id, cleaned_text in CLEAN.items():
        mask = df["replacement_id"] == replacement_id

        df.loc[mask, "hygiene_status"] = "keep_cleaned"
        df.loc[mask, "cleaned_claim_text"] = cleaned_text
        df.loc[mask, "hygiene_notes"] = (
            "corrected_extraction_spacing_artifact"
        )

    df.to_csv(
        PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("Replacement hygiene adjudication v1")
    print("===================================")
    print(df["hygiene_status"].value_counts().to_string())

    valid = df[
        df["hygiene_status"].isin(
            ["keep", "keep_cleaned"]
        )
    ]

    print()
    print("Valid replacements:", len(valid))
    print(
        "Excluded replacements:",
        int(
            (df["hygiene_status"] == "exclude_noise").sum()
        ),
    )


if __name__ == "__main__":
    main()