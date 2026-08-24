"""
Loads prompts/system_prompt.md, injects the generated schema block from
prompts/schema_block.md in place of the {{SCHEMA_BLOCK}} placeholder, and
returns the final assembled prompt string the agent will actually use.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
TEMPLATE_PATH = PROMPTS_DIR / "system_prompt.md"
SCHEMA_BLOCK_PATH = PROMPTS_DIR / "schema_block.md"
PLACEHOLDER = "{{SCHEMA_BLOCK}}"


def get_system_prompt() -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Missing {TEMPLATE_PATH}."
        )
    if not SCHEMA_BLOCK_PATH.exists():
        raise FileNotFoundError(
            f"Missing {SCHEMA_BLOCK_PATH}."
        )

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    schema_block = SCHEMA_BLOCK_PATH.read_text(encoding="utf-8").strip()

    if PLACEHOLDER not in template:
        raise ValueError(
            f"{PLACEHOLDER} placeholder not found in {TEMPLATE_PATH}. "
        )

    return template.replace(PLACEHOLDER, schema_block)