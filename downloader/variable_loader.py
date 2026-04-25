"""Load and validate a topic YAML file.

Returns:
    variables   — flat list of all variable codes in declaration order
    var_to_group — dict mapping each code to its sub-theme label
"""

import re
from pathlib import Path

import yaml

# Census variable code pattern: one uppercase letter, digits, underscore, digits, E or M
_VAR_RE = re.compile(r"^[A-Z][0-9]+_[0-9]+[EM]$")
# Special Census API pseudo-variables that don't follow the standard pattern
_SPECIAL_VARS = {"NAME", "GEO_ID", "GEOID"}


def load_topic(topic: str, config_dir: Path) -> tuple[list[str], dict[str, str]]:
    yaml_path = config_dir / "topics" / f"{topic}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Topic file not found: {yaml_path}\n"
            f"Available topics: {[p.stem for p in (config_dir / 'topics').glob('*.yaml')]}"
        )

    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)

    groups = config.get("variable_groups", {})
    if not groups:
        raise ValueError(f"No variable_groups found in {yaml_path}")

    variables: list[str] = []
    var_to_group: dict[str, str] = {}
    invalid: list[str] = []

    for _key, group in groups.items():
        label = group.get("label", _key)
        for code in group.get("variables", []):
            if code not in _SPECIAL_VARS and not _VAR_RE.match(code):
                invalid.append(code)
                continue
            if code not in var_to_group:  # deduplicate across groups
                variables.append(code)
                var_to_group[code] = label

    if invalid:
        raise ValueError(
            f"Invalid variable codes in {yaml_path}:\n  " + "\n  ".join(invalid)
        )

    return variables, var_to_group


def load_cities(config_dir: Path) -> dict:
    yaml_path = config_dir / "cities.yaml"
    with yaml_path.open() as fh:
        return yaml.safe_load(fh)
