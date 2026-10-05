"""Shared input string types.

Every free-text field that ends up in the DOCX goes through one of these, because python-docx
raises on XML-incompatible characters (a 500 on `/lineups`, and a saved lineup that could never
be generated), and tabs/newlines would be written into the document as real tabs and line
breaks that shift the layout. Whitespace-only values are blank, not names.
"""

import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, StringConstraints

_XML_NONCHARACTERS = {"￾", "￿"}


def reject_unsafe_characters(value: str) -> str:
    for char in value:
        if unicodedata.category(char) in {"Cc", "Cs"} or char in _XML_NONCHARACTERS:
            raise ValueError("must not contain control characters")
    return value


def blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def clean_str(max_length: int):
    """Stripped, non-empty, length-capped text without control characters."""
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length),
        AfterValidator(reject_unsafe_characters),
    ]


def optional_clean_str(max_length: int):
    """Like `clean_str`, but a blank value (`""`, spaces) means "not provided" (`None`)."""
    return Annotated[clean_str(max_length) | None, BeforeValidator(blank_to_none)]


CleanStr50 = clean_str(50)
CleanStr100 = clean_str(100)
CleanStr120 = clean_str(120)
CleanStr200 = clean_str(200)

OptionalCleanStr50 = optional_clean_str(50)
OptionalCleanStr120 = optional_clean_str(120)
OptionalCleanStr200 = optional_clean_str(200)
