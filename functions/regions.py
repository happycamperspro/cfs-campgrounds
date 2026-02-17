"""
US state-to-region and state abbreviation mappings.
"""
from typing import Dict

REGIONS = {
    "Northeast": ["CT", "DE", "MA", "MD", "ME", "NH", "NJ", "NY", "PA", "RI", "VT"],
    "Southeast": ["AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"],
    "Midwest": ["IA", "IL", "IN", "KS", "MI", "MN", "MO", "ND", "NE", "OH", "OK", "SD", "WI"],
    "Southwest": ["AZ", "NM", "TX", "UT"],
    "Rocky Mountain": ["CO", "ID", "MT", "WY"],
    "Pacific Northwest": ["OR", "WA"],
    "Pacific": ["CA", "HI"],
    "Alaska": ["AK"],
}

# Build reverse lookup: state code -> region
STATE_TO_REGION: Dict[str, str] = {}
for region, states in REGIONS.items():
    for state in states:
        STATE_TO_REGION[state] = region

# DC special case
STATE_TO_REGION["DC"] = "Northeast"

STATE_ABBREVIATIONS: Dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}

# Reverse: abbreviation -> full name
ABBREVIATION_TO_STATE: Dict[str, str] = {v: k for k, v in STATE_ABBREVIATIONS.items()}


def get_region(state_code: str) -> str:
    """Return the region for a given 2-letter state code."""
    return STATE_TO_REGION.get(state_code.upper(), "Unknown")


def normalize_state(state_input: str) -> str:
    """Convert full state name to 2-letter code, or return as-is if already a code."""
    if not state_input:
        return ""
    if len(state_input) <= 2:
        return state_input.upper()
    return STATE_ABBREVIATIONS.get(state_input.title(), state_input)


def get_state_full_name(state_code: str) -> str:
    """Return full state name for a 2-letter code."""
    return ABBREVIATION_TO_STATE.get(state_code.upper(), "")
