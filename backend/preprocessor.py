
from pathlib import Path
import json
import re
import html

import numpy as np
import pandas as pd


BASE_DIR=Path(__file__).resolve().parent


CONFIG=json.loads(
    (
        BASE_DIR/
        "preprocess_config.json"
    ).read_text(
        encoding="utf-8"
    )
)


STOPWORDS={
    str(x).lower()
    for x in CONFIG.get(
        "stopwords",
        []
    )
}


LEMMA_MAP={
    str(k).lower():str(v)
    for k,v in CONFIG.get(
        "lemma_map",
        {}
    ).items()
}


INPUT_COLUMNS=list(
    CONFIG.get(
        "input_columns",
        []
    )
)


MAX_CHARACTERS=int(
    CONFIG.get(
        "max_characters",
        1000
    )
)


def clean_text(text):

    text=html.unescape(
        str(text)
    )

    text=text.lower()

    text=re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    text=re.sub(
        r"@\w+",
        " ",
        text
    )

    text=re.sub(
        r"#(\w+)",
        r"\1",
        text
    )

    text=re.sub(
        r"[^a-z0-9\s']",
        " ",
        text
    )

    text=re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def preprocess(text):

    if not isinstance(text,str):
        raise TypeError(
            "Tweet text must be a string."
        )

    raw=text.strip()

    if not raw:
        raise ValueError(
            "Tweet text cannot be empty."
        )

    if len(raw)>MAX_CHARACTERS:
        raise ValueError(
            f"Tweet text exceeds the "
            f"{MAX_CHARACTERS:,}-character limit."
        )

    clean=clean_text(
        raw
    )

    if not clean:
        raise ValueError(
            "Tweet contains no usable text after preprocessing."
        )

    tokens=clean.split()

    filtered=[
        token
        for token in tokens
        if token.lower()
        not in STOPWORDS
    ]

    lemmas=[
        LEMMA_MAP.get(
            token.lower(),
            token
        )
        for token in filtered
    ]

    final_text=(
        " ".join(
            lemmas
        ).strip()
        or clean
    )

    values={
        "record_id":-1,
        "id":-1,
        "keyword":"no keyword",
        "location":"no location",
        "text":raw,
        "original_text":raw,
        "clean_text":clean,
        "tokens":tokens,
        "filtered_tokens":filtered,
        "lemmatized_tokens":lemmas,
        "final_text":final_text
    }

    row=pd.DataFrame(
        [values]
    )

    for col in INPUT_COLUMNS:
        if col not in row.columns:
            row[col]=np.nan

    ordered=[
        c
        for c in INPUT_COLUMNS
        if c in row.columns
    ]

    extras=[
        c
        for c in row.columns
        if c not in ordered
    ]

    return row[
        ordered+extras
    ]
