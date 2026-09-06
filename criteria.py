"""
Acceptance criteria as structured data, plus a deterministic evaluator.

Pass/fail against a stated numeric limit is arithmetic, not judgment. We do it
in code so the result is reproducible and cannot be hallucinated. The model is
used only where judgment is genuinely required: interpreting observations and
writing the recommendation.

Criteria mirror SOP-PMP-114 Rev. 4, Section 2.
"""

import re

SOURCE_DOC = "SOP-PMP-114-limits"
SOURCE_PAGE = "Section 2"

# direction "min": higher is better.  direction "max": lower is better.
CRITERIA = [
    {
        "key": "wall_thickness",
        "label": "Casing wall thickness (minimum measured)",
        "match_all": ["wall thickness"],
        "extract": r"([\d.]+)\s*mm(?!/)",
        "unit": "mm",
        "direction": "min",
        "acceptable": 5.0,
        "action": 4.5,
        "text": "acceptable 5.0 mm or greater; alert 4.5 to 5.0 mm; action limit below 4.5 mm",
    },
    {
        "key": "vib_nde",
        "label": "Bearing housing vibration, non-drive end (RMS)",
        "match_all": ["vibration", "non-drive"],
        "extract": r"([\d.]+)\s*mm/s",
        "unit": "mm/s RMS",
        "direction": "max",
        "acceptable": 4.5,
        "action": 7.1,
        "text": "acceptable 4.5 mm/s or less; alert 4.5 to 7.1 mm/s; action limit above 7.1 mm/s",
    },
    {
        "key": "vib_de",
        "label": "Bearing housing vibration, drive end (RMS)",
        "match_all": ["vibration", "drive end"],
        "match_none": ["non-drive"],
        "extract": r"([\d.]+)\s*mm/s",
        "unit": "mm/s RMS",
        "direction": "max",
        "acceptable": 4.5,
        "action": 7.1,
        "text": "acceptable 4.5 mm/s or less; alert 4.5 to 7.1 mm/s; action limit above 7.1 mm/s",
    },
    {
        "key": "bearing_temp",
        "label": "Bearing housing temperature",
        "match_all": ["temperature"],
        "extract": r"([\d.]+)\s*°?\s*C",
        "unit": "degrees C",
        "direction": "max",
        "acceptable": 80.0,
        "action": 95.0,
        "text": "acceptable 80 C or less; alert 80 to 95 C; action limit above 95 C",
    },
    {
        "key": "discharge_stability",
        "label": "Discharge pressure stability over 10 minutes",
        "match_all": ["discharge pressure"],
        "extract": r"(?:±|\+/-|plus or minus)\s*([\d.]+)\s*bar",
        "unit": "bar variation",
        "direction": "max",
        "acceptable": 0.3,
        "action": 0.8,
        "text": "acceptable plus or minus 0.3 bar; alert 0.3 to 0.8 bar; action limit above plus or minus 0.8 bar",
        "note_if_missing": "stable, no fluctuation recorded",
    },
    {
        "key": "current_stability",
        "label": "Motor current stability over 10 minutes",
        "match_all": ["motor current"],
        "extract": r"(?:±|\+/-|plus or minus)\s*([\d.]+)\s*%",
        "unit": "percent variation",
        "direction": "max",
        "acceptable": 3.0,
        "action": 7.0,
        "text": "acceptable plus or minus 3 percent; alert 3 to 7 percent; action limit above plus or minus 7 percent",
        "note_if_missing": "stable, no fluctuation recorded",
    },
    {
        "key": "strainer_dp",
        "label": "Suction strainer differential pressure",
        "match_all": ["strainer"],
        "extract": r"([\d.]+)\s*bar",
        "unit": "bar",
        "direction": "max",
        "acceptable": 0.35,
        "action": 0.50,
        "text": "acceptable 0.35 bar or less; alert 0.35 to 0.50 bar; action limit above 0.50 bar",
    },
]

# Qualitative criterion, matched on keywords rather than numbers.
SEAL_CRITERION = {
    "label": "Mechanical seal leakage",
    "match_all": ["seal"],
    "text": "acceptable no visible leakage; alert intermittent weeping; "
            "action limit continuous drip or spray",
    "rules": [
        (["continuous", "drip", "spray"], "action"),
        (["weep", "intermittent", "seep"], "alert"),
        (["no visible", "no leak", "none"], "acceptable"),
    ],
}


def _matches(param_text, crit):
    low = param_text.lower()
    if any(bad in low for bad in crit.get("match_none", [])):
        return False
    return all(term in low for term in crit["match_all"])


def _number(value_text, pattern):
    m = re.search(pattern, value_text, re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _severity(value, crit):
    if crit["direction"] == "min":
        if value >= crit["acceptable"]:
            return "acceptable"
        if value >= crit["action"]:
            return "alert"
        return "action"
    if value <= crit["acceptable"]:
        return "acceptable"
    if value <= crit["action"]:
        return "alert"
    return "action"


def _describe(crit, value, severity):
    unit = crit["unit"]
    if severity == "action":
        bound = crit["action"]
        word = "below" if crit["direction"] == "min" else "above"
        return (f"Measured {value} {unit}, which is {word} the action limit of "
                f"{bound} {unit}. This is a deviation requiring disposition under "
                f"SOP-PMP-114 Section 5.")
    if severity == "alert":
        return (f"Measured {value} {unit}, which falls in the alert band. A repeat "
                f"measurement is required within 7 days.")
    return f"Measured {value} {unit}, within the acceptable range."


def evaluate(measurements):
    """
    measurements: list of objects with .parameter and .value (strings).
    Returns (findings, unmatched) where findings are plain dicts.
    """
    findings = []
    matched_params = set()

    for crit in CRITERIA:
        for m in measurements:
            if not _matches(m.parameter, crit):
                continue

            value = _number(m.value, crit["extract"])
            if value is None:
                if "note_if_missing" in crit:
                    findings.append({
                        "parameter": crit["label"],
                        "measured_value": m.value,
                        "applicable_limit": crit["text"],
                        "severity": "acceptable",
                        "description": f"Recorded as {crit['note_if_missing']}.",
                        "source_doc": SOURCE_DOC,
                        "source_page": SOURCE_PAGE,
                    })
                    matched_params.add(m.parameter)
                continue

            sev = _severity(value, crit)
            findings.append({
                "parameter": crit["label"],
                "measured_value": m.value,
                "applicable_limit": crit["text"],
                "severity": sev,
                "description": _describe(crit, value, sev),
                "source_doc": SOURCE_DOC,
                "source_page": SOURCE_PAGE,
            })
            matched_params.add(m.parameter)
            break

    # qualitative seal check
    for m in measurements:
        if not _matches(m.parameter, SEAL_CRITERION):
            continue
        low = m.value.lower()
        sev = "acceptable"
        for keywords, level in SEAL_CRITERION["rules"]:
            if any(k in low for k in keywords):
                sev = level
                break
        findings.append({
            "parameter": SEAL_CRITERION["label"],
            "measured_value": m.value,
            "applicable_limit": SEAL_CRITERION["text"],
            "severity": sev,
            "description": f"Recorded as: {m.value}.",
            "source_doc": SOURCE_DOC,
            "source_page": SOURCE_PAGE,
        })
        matched_params.add(m.parameter)
        break

    unmatched = [m.parameter for m in measurements if m.parameter not in matched_params]

    order = {"action": 0, "alert": 1, "acceptable": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 3))
    return findings, unmatched


def summarise(findings):
    counts = {"action": 0, "alert": 0, "acceptable": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    if counts["action"]:
        return "deviations_found", counts
    if counts["alert"]:
        return "alerts_only", counts
    return "no_deviations", counts