"""
Verifies schema injection works correctly: loads the
template, injects the real schema block, and sanity-checks.
"""

from prompts.prompt_loader import get_system_prompt


def main():
    print("Assembling system prompt...")
    prompt = get_system_prompt()

    assert "{{SCHEMA_BLOCK}}" not in prompt, (
        "Placeholder was not replaced — schema injection failed silently."
    )
    print("  OK — placeholder was replaced.")

    # Sanity check against your actual known tables from sub-problem 2.
    # Update these if your schema changes later.
    expected_fragments = ["constructors", "f1_results"]
    for fragment in expected_fragments:
        assert fragment in prompt, (
            f"Expected '{fragment}' in the assembled prompt but it's missing. "
            "Check prompts/schema_block.md was generated correctly."
        )
        print(f"  OK — found expected table reference: '{fragment}'")

    assert "Read-only only" in prompt, "Core rules section seems to be missing from the template."
    print("  OK — rules section present.")

    print(f"\nAssembled prompt length: {len(prompt)} characters")
    print("\n--- Preview (first 600 chars) ---")
    print(prompt[:600])
    print("--- End preview ---")

    print("\nAll checks passed. Sub-problem 3 is working correctly.")


if __name__ == "__main__":
    main()