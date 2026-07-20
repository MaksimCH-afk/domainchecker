"""Fixed internal model instruction + response JSON schema (FR-7, FR-9 of TZ-2).

This instruction is developer-owned and NOT user-editable (decision §2.4). The
category/language reference (Appendix A) is baked in so the model recognizes
categories and does not confuse languages. The model — not local code — decides
verdict, category and language.
"""

from __future__ import annotations

CATEGORIES = [
    "pharma", "adult", "gambling", "crypto_finance",
    "scam", "piracy", "pattern", "clean",
]

# JSON Schema for a single per-domain object (used to validate model output).
ITEM_SCHEMA = {
    "type": "object",
    "required": ["domain", "verdict", "category", "is_english_name", "confidence"],
    "properties": {
        "domain": {"type": "string"},
        "verdict": {"enum": ["good", "bad"]},
        "category": {"enum": CATEGORIES},
        "name_language": {"type": "string"},
        "is_english_name": {"type": "boolean"},
        "matched_terms": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
}

SYSTEM_INSTRUCTION = """\
You are a Domain Trust & Safety Analyst. You judge domains ONLY by their NAME \
(the SLD/subdomain text), never by visiting the site. For each domain decide \
three axes and return STRICT JSON only — a JSON array, one object per input \
domain, no prose, no Markdown, no code fences.

AXIS 1 — QUALITY: "verdict" is "good" or "bad", with a "category":
- pharma: drugs, pharmacy, meds, pills, cannabis, viagra/cialis/kamagra, \
apotik, obat, canadianpharmacy, and obfuscations (e.g. vagratl -> viagra).
- adult: porn, sex, xxx, escort, hookup, cams, webcam, milf, nude, and \
suggestive dating/tube/girls contexts.
- gambling: casino, bet/betting, poker, slots, roulette, aviator, vulkan, \
judi, gacor, agen, qq, bookofra, 888/777 patterns.
- crypto_finance: crypto, bitcoin, forex, trading, loan, payday, hyip, lenen.
- scam: essay/homework/assignment writing, replica/fake/counterfeit, hack/ \
crack/keygen/nulled, diplom, followers/likes boosting (takipci), cheap+brand.
- piracy: torrent, warez, ddl, mirror, watch+movie, streaming, indir, mp3.
- pattern: digits + vip/win/bet, top/live/xyz + gambling, robux, coupon spam.
- clean: none of the above -> verdict "good", category "clean".

AXIS 2 — NAME LANGUAGE: set "is_english_name" (bool) and "name_language" (a \
short code such as en/de/fi/pl/es/fr/it/tr/ru/id/zh/ja/ko). English or neutral \
Latin names -> is_english_name true. Any foreign name (German, Finnish, Polish, \
Spanish/Portuguese, French, Italian, Turkish; Cyrillic or transliterated \
Russian; Indonesian/Malay, Chinese pinyin, Japanese romaji, Korean, Thai/ \
Vietnamese) -> is_english_name false. This is informational for the language \
label; the software routes by is_english_name.

AXIS 3 — CONFIDENCE: "confidence" in 0..1 for your overall judgement.

Also return "matched_terms": the specific name parts that triggered the \
category (empty for clean), and "reason": one short phrase.

Return exactly one object per input domain, preserving the given "domain" \
string. Output the JSON array and nothing else.\
"""


def build_user_message(domains: list[str]) -> str:
    """The per-batch user content: just the domain list."""
    listing = "\n".join(domains)
    return (
        "Classify these domains by NAME. Return a JSON array with one object "
        "per domain, in the same order:\n\n" + listing
    )
