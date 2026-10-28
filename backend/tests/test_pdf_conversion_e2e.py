"""End-to-end PDF fidelity checks against the running containerized API.

These tests exercise the *real* LibreOffice conversion (which only exists inside the
container), so they are marked ``e2e`` and deselected from the default ``task test`` run.
Run them with ``task test-e2e`` (which builds the image, starts the container, and tears it
down afterwards) or point ``LINEUP_API_URL`` at an already-running instance.

We deliberately do NOT diff the rendered pixels against ``expected-rajtlista.pdf``: that
reference was produced with the real (proprietary) Calibri font, while the container renders
with Carlito. Carlito is *metric-compatible* with Calibri (identical advance widths) but not
glyph-identical, so a pixel diff would flag harmless shape differences. Instead we assert the
properties that actually encode "the layout is correct": a single page, all expected text
present, the title near the top, and — most tellingly — that word widths and key x-positions
match the reference. Word width is a direct, layout-engine-independent measure of font
metrics, so it is exactly what breaks when the Calibri substitute is missing.
"""

import io
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import jwt
import pytest

pdfplumber = pytest.importorskip("pdfplumber")

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("LINEUP_API_URL", "http://127.0.0.1:8000")
READINESS_TIMEOUT_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 180

# `task test-e2e` runs scripts/e2e_keys.py before starting the container and compose.e2e.yml makes
# the container trust that key (SUPABASE_URL=http://localhost:9999 inside its namespace).
AUTH_DIR = Path(os.environ.get("E2E_AUTH_DIR", Path(__file__).parents[2] / ".e2e-auth"))
E2E_ISSUER = "http://localhost:9999/auth/v1"
E2E_KEY_ID = "e2e-key"

REFERENCE_PDF = Path(__file__).parent / "resources" / "expected-rajtlista.pdf"

# Same data used to author tests/resources/expected-rajtlista.pdf (mirrors
# conftest.valid_payload) so the generated document can be compared against the reference.
PAYLOAD = {
    "match": "SZVTK - Csongrád",
    "division": "OB II.",
    "team_name": "SZVTK",
    "cap": "Fehér",
    "date": "2024. 12. 21.",
    "coach": "Török András",
    "doctor": "Török András",
    "assistant_coach": "Török András",
    "team_leader": "Török András",
    "ball_thrower": "Török András",
    "players": [
        {
            "cap_number": i,
            "name": "Török András",
            "nssz_number": f"MVLSZ{123456788 + i}",
        }
        for i in range(1, 16)
    ],
}

EXPECTED_TEXT = [
    "MAGYAR VÍZILABDA SZÖVETSÉG",
    "RAJTLISTA",
    "Mérkőzés:",
    "SZVTK - Csongrád",
    "Osztály:",
    "OB II.",
    "Csapat neve:",
    "Fehér",
    "Kék",
    "Dátum:",
    "2024. 12. 21.",
    "Sapkaszám",
    "Név",
    "NSSZ szám",
    "MVLSZ123456789",
    "Edző:",
    "Hivatalos orvos:",
    "Segédedző:",
    "Csapatvezető:",
    "Labdabedobó:",
    "Csapatvezető aláírása",
]

# Tolerances in PDF points. Carlito shares Calibri's advance widths, so widths and tab-anchored
# positions land within a couple of points of the reference; a non-metric-compatible fallback
# font drifts well beyond these.
WIDTH_TOLERANCE = 6.0
X_TOLERANCE = 20.0


def _wait_for_server() -> bool:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


def _find_word(words, text):
    """First extracted word whose text matches exactly, in reading order."""
    for word in words:
        if word["text"] == text:
            return word
    return None


def _access_token() -> str:
    """A token for a made-up user, signed with the throw-away key the container trusts."""
    private_key = AUTH_DIR / "private.pem"
    if not private_key.exists():
        pytest.skip(
            f"No e2e signing key at {private_key}; run the whole flow with `task test-e2e`."
        )
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": E2E_ISSUER,
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(
        claims,
        private_key.read_text(),
        algorithm="ES256",
        headers={"kid": E2E_KEY_ID},
    )


@pytest.fixture(scope="session")
def generated_pdf_bytes() -> bytes:
    if not _wait_for_server():
        pytest.skip(
            f"Lineup API not reachable at {BASE_URL}; start it with `task up` "
            f"or run the whole flow with `task test-e2e`."
        )
    request = urllib.request.Request(
        f"{BASE_URL}/lineups?format=pdf",
        data=json.dumps(PAYLOAD).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_access_token()}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        assert resp.status == 200
        assert resp.headers["content-type"] == "application/pdf"
        # The API is public: no browser or proxy may keep a copy of the roster document.
        assert resp.headers["cache-control"] == "no-store"
        assert resp.headers["x-content-type-options"] == "nosniff"
        return resp.read()


def test_post_lineups_without_a_token_is_rejected():
    if not _wait_for_server():
        pytest.skip(f"Lineup API not reachable at {BASE_URL}")
    request = urllib.request.Request(
        f"{BASE_URL}/lineups",
        data=json.dumps(PAYLOAD).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)
    assert exc.value.code == 401


@pytest.fixture(scope="session")
def generated_pdf(generated_pdf_bytes):
    with pdfplumber.open(io.BytesIO(generated_pdf_bytes)) as pdf:
        yield pdf


@pytest.fixture(scope="session")
def reference_words():
    if not REFERENCE_PDF.exists():
        pytest.skip(f"reference PDF not found at {REFERENCE_PDF}")
    with pdfplumber.open(str(REFERENCE_PDF)) as pdf:
        words = pdf.pages[0].extract_words()
    if not words:
        pytest.skip("reference PDF has no extractable text layer")
    return words


def test_response_is_pdf(generated_pdf_bytes):
    assert generated_pdf_bytes[:4] == b"%PDF"


def test_pdf_is_single_page(generated_pdf):
    assert len(generated_pdf.pages) == 1, (
        f"expected a single page, got {len(generated_pdf.pages)} — "
        f"content likely overflowed due to a font/layout regression"
    )


def test_pdf_contains_expected_text(generated_pdf):
    text = generated_pdf.pages[0].extract_text() or ""
    normalized = " ".join(text.split())
    missing = [s for s in EXPECTED_TEXT if " ".join(s.split()) not in normalized]
    assert not missing, f"missing expected text: {missing}"


def test_all_cap_numbers_present(generated_pdf):
    words = {w["text"] for w in generated_pdf.pages[0].extract_words()}
    missing = [str(n) for n in range(1, 16) if str(n) not in words]
    assert not missing, f"missing cap numbers: {missing}"


def test_title_is_near_top(generated_pdf):
    title = _find_word(generated_pdf.pages[0].extract_words(), "RAJTLISTA")
    assert title is not None, "RAJTLISTA title not found"
    assert title["top"] < 160, (
        f"title unexpectedly low on the page (top={title['top']:.1f})"
    )


def test_word_widths_match_reference(generated_pdf, reference_words):
    """Word width is a direct measure of font metrics; Carlito must match Calibri here."""
    gen_words = generated_pdf.pages[0].extract_words()
    for token in ["RAJTLISTA", "Sapkaszám", "Csapatvezető", "MVLSZ123456789"]:
        gen = _find_word(gen_words, token)
        ref = _find_word(reference_words, token)
        assert gen is not None, f"{token!r} missing from generated PDF"
        assert ref is not None, f"{token!r} missing from reference PDF"
        gen_width = gen["x1"] - gen["x0"]
        ref_width = ref["x1"] - ref["x0"]
        assert abs(gen_width - ref_width) <= WIDTH_TOLERANCE, (
            f"{token!r} width {gen_width:.1f}pt vs reference {ref_width:.1f}pt — "
            f"font metrics differ (Calibri substitute likely missing)"
        )


def test_key_positions_match_reference(generated_pdf, reference_words):
    """Left-margin and tab-anchored x-positions should line up with the reference."""
    gen_words = generated_pdf.pages[0].extract_words()
    for token in ["Osztály:", "Fehér", "Kék"]:
        gen = _find_word(gen_words, token)
        ref = _find_word(reference_words, token)
        assert gen is not None, f"{token!r} missing from generated PDF"
        assert ref is not None, f"{token!r} missing from reference PDF"
        assert abs(gen["x0"] - ref["x0"]) <= X_TOLERANCE, (
            f"{token!r} x0 {gen['x0']:.1f} vs reference {ref['x0']:.1f} — layout drift"
        )
