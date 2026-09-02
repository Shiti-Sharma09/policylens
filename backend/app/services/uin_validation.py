"""
IRDAI UIN (Unique Identification Number) sanity-checking for newly-added reference
policy PDFs, per the working convention: "validate it from IRDAI UIN" before trusting
a new document (day4_query_answers.md's follow-up section has the full reasoning).

Important limitation: there is no public IRDAI API to query a UIN live. IRDAI only
publishes a downloadable product list (PDF/Excel) on irdai.gov.in, republished
periodically. So "validate" here means two separate things, and only the first is
automatable:

1. Structural sanity check (this file) - every real UIN observed across this project's
   8 reference PDFs follows the fixed shape IRDAN<3-digit insurer code><2-letter product
   category><digits>V<digits>, 23 characters total. This catches an obviously fabricated
   or mistyped UIN (wrong prefix, wrong length, lowercase-only, garbage characters) before
   it's trusted. It is NOT proof of authenticity - a well-formed fake would still pass.
2. Manual cross-check against IRDAI's actual published product list for that insurer -
   this is the step that actually confirms a UIN is real, and it's what was actually done
   for all 8 existing reference PDFs (see PROGRESS.md's Day 2 audit). There's no way to
   automate this without scraping/parsing IRDAI's periodically-republished list, which is
   out of scope unless dataset expansion is scoped and prioritized.

The regex below is inferred from the 3 UINs actually on record in this project
(IRDAN115RP0007V01201819, IRDAN125RP0002V01201920, IRDAN115RP0002V01201920), not from
IRDAI's own published spec (no single authoritative machine-readable spec was found) -
treat a "valid" result as "shaped like the real ones we've seen", not as a guarantee.
"""

import re

_UIN_PATTERN = re.compile(r"^IRDAN\d{3}[A-Z]{2}\d{3,7}V\d{6,8}$")
_UIN_IN_TEXT_PATTERN = re.compile(r"\bIRDAN\d{3}[A-Z]{2}\d{3,7}V\d{6,8}\b")


def validate_uin_format(uin: str) -> bool:
    """Coarse structural check only - see this module's docstring. Always still cross-
    check a new document's UIN against IRDAI's published product list by hand."""
    return bool(_UIN_PATTERN.match(uin.strip().upper()))


def extract_uin(text: str) -> str | None:
    """Pulls the first UIN-shaped token out of raw extracted policy text, if present -
    used when adding a new reference PDF so its UIN surfaces automatically for the
    manual IRDAI cross-check, instead of requiring someone to hunt for it by eye."""
    match = _UIN_IN_TEXT_PATTERN.search(text.upper())
    return match.group(0) if match else None
