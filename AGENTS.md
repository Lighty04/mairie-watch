# AGENTS.md - {PROJECT_NAME}

## Project Overview

Brief description of what this project does.

## Git Repository

**GitHub URL:** https://github.com/Lighty04/{repo-name}

**Local Path:** ~/.openclaw/workspace/{project-folder}/

**Created:** YYYY-MM-DD

## Tech Stack

- Language/Framework:
- Database (if any):
- Deployment target:

## QA & Testing

All projects use the common QA framework. See `skills/non-regression-testing/SKILL.md` for details.

### Running Tests

```bash
# Run all tests
python3 tests/run_tests.py

# Run specific test
python3 tests/test_specific_feature.py
```

### Pre-Deployment Checklist

- [ ] All tests pass: `python3 tests/run_tests.py`
- [ ] No "Erreur" or error messages in output
- [ ] Manual verification complete (if applicable)

### Non-Regression Tests

When fixing a bug:
1. Create test in `tests/test_bug_[description].py`
2. Verify it catches the bug before fixing
3. Apply fix
4. Verify test passes

See `tests/template_test.py` for boilerplate.

## Deployment

1. Run QA tests (main agent spawns devclaw)
2. Devclaw deploys to server
3. Verify deployment succeeds

## Project-Specific Rules

Add any rules specific to this project here.

## Design System

**REQUIRED:** All web projects must include `DESIGN.md` at the project root.

- **Source:** Copy from `~/workspace/DESIGN.md` (workspace root)
- **Customization:** Update the "Project-Specific Notes" section for this project
- **Consistency:** Follow the design tokens, spacing, colors, and component specs defined in DESIGN.md
- **Dark mode default:** Unless user explicitly requests light mode
- **No exceptions:** Every web project gets a DESIGN.md, even simple tools

**First step for any web project:**
1. Copy DESIGN.md from workspace root
2. Set project-specific accent color
3. Update project-specific notes section
4. Then proceed with implementation

This ensures all LightyClaw projects have consistent, professional UI.
