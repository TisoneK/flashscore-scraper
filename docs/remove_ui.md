# Plan: Remove UI Components for Console-Only Application

## Objective
Transition the project to a strictly console (CLI) application by removing all UI-related code, dependencies, and documentation.

---

## Step-by-Step Plan

### 1. Identify UI Components
- Locate all files and directories related to the UI:
  - `src/ui/` (all subfolders and files)
  - Any UI-related scripts in `src/scripts/` (e.g., `run_ui.py`)
  - UI references in documentation (e.g., `src/ui/README.md`)

### 2. Remove UI Code
- Delete the entire `src/ui/` directory.
- Remove UI-related scripts (e.g., `src/scripts/run_ui.py`).
- Remove any UI-specific configuration or settings.

### 3. Refactor CLI and Core Logic
- Ensure all user interaction is handled via the CLI (`src/cli/`).
- Refactor any code that previously depended on UI modules to use CLI alternatives or remove the dependency.
- Update imports and references throughout the codebase.

### 4. Update Documentation
- Remove or update documentation that references the UI (e.g., `src/ui/README.md`, main `README.md`).
- Add a note in the main `README.md` and `docs/` that the project is now CLI-only.
- Document any new CLI commands or changes in usage.

### 5. Update Dependencies
- Remove UI-related dependencies from `requirements.txt` and `pyproject.toml` (e.g., Streamlit, PySimpleGUI, etc.).
- Run dependency management tools to ensure only necessary packages remain.

### 6. Update Tests
- Remove or refactor tests that depend on UI components.
- Ensure all remaining tests pass and cover CLI functionality.

### 7. Final Review
- Test the application end-to-end via the CLI.
- Confirm there are no remaining UI references or dead code.
- Update versioning and changelogs as appropriate.

---

## Checklist
- [ ] UI code and scripts removed
- [ ] CLI refactored and tested
- [ ] Documentation updated
- [ ] Dependencies cleaned
- [ ] Tests updated
- [ ] Final review complete 