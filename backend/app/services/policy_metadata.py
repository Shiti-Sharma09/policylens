"""
Lightweight, regex-based extraction of structured facts from policy text that are
reliably stated in a fixed, formulaic way - as opposed to Day 5's planned LLM-based
structured extraction (premium, IDV, deductible, etc.), which needs real reasoning
over free-form clauses. Tenure doesn't: IRDAI-filed wordings state it directly in the
title using one of a small number of fixed phrasings.

First field: policy tenure (declared product duration). This exists specifically to
avoid a real comparison bias found during Day 2's authenticity audit - two reference
policies of the same structural_type (third_party_only) turned out to have different
tenures (3-year vs annual), which would bias a naive price/coverage comparison in
Day 5 if tenure weren't tracked.

Only 3 of the current 8 reference PDFs actually state a tenure at all - the rest are
generic "STANDARD FORM" wordings with no duration baked into the template (real
start/end dates live on a customer-specific policy Schedule, which isn't part of the
wording document). Returning None for those is correct, not a detection failure -
never guess a tenure that isn't actually stated.
"""

import re

# Restricted to the first 400 chars (title/header area) - the full document text
# contains false positives further in, e.g. HDFC's SAOD depreciation table says
# "Exceeding 3 years but not exceeding 4 years" which is about vehicle age, not
# policy tenure. Confirmed empirically against all 8 reference PDFs: zero false
# positives and zero false negatives with this exact pattern.
_TENURE_YEARS_PATTERN = re.compile(r"\b(\d{1,2})\s+YEARS?\s*-")
_ANNUAL_PATTERN = re.compile(r"-\s*ANNUAL\b")


def detect_tenure_years(text: str) -> int | None:
    head = text[:400].upper()
    match = _TENURE_YEARS_PATTERN.search(head)
    if match:
        return int(match.group(1))
    if _ANNUAL_PATTERN.search(head):
        return 1
    return None
