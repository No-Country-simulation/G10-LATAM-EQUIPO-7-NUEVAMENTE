import re
import unicodedata


def clean_text(text: str) -> str:

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    return "\n".join(lines).strip()