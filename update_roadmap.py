with open("ROADMAP.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "TASK-14" in line and "Adriraj" in line:
        lines[i] = "  - `TASK-14` (Rajdeep): Automated benchmark trace and fixture validation suite (`tests/contract/test_fixtures_validate.py`).\n"
    if "TASK-15" in line and "Daksh" in line:
        lines[i] = "  - `TASK-15` (Rajdeep): Automated decision correctness and verification independence suite (`tests/contract/test_verification_independence.py`).\n"

with open("ROADMAP.md", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Updated ROADMAP.md via script!")

