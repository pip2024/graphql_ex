"""Export the GraphQL schema to a .graphql SDL file.

Run with: python scripts/export_schema.py

This is the programmatic equivalent of the `strawberry export-schema`
CLI command (see README for that route). Having a plain script instead
means a CI pipeline can run it without needing the `strawberry` console
entry point installed on PATH, and it's easy to extend (e.g. also
diff against the previous version to catch breaking changes).
"""

from __future__ import annotations

from pathlib import Path

from app.schema.schema import schema

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "schema.graphql"


def main() -> None:
    OUTPUT_PATH.write_text(str(schema))
    print(f"Wrote schema to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
