"""
Purpose: Generates JSON Schema and frontend types from the contracts.
Owner: Rajdeep

Documented Gap:
The documented toolchain and output paths for JSON Schema and TypeScript
type generation are not yet established in the repository. As per the
architectural guidelines, this gap is documented here rather than
inventing a parallel schema generation system or creating arbitrary
output paths.

Once the frontend toolchain and schema registry paths are formally defined,
this script should be updated to use Pydantic's `schema_json()` / `model_json_schema()`
to export the models from `src/slokern/contracts/` as the single source of truth.
"""

if __name__ == "__main__":
    print("Schema generation toolchain is not yet established. See documented gap in this file.")
