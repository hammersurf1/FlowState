@echo off
REM Run formatting tests headlessly (no prompts). Exits non-zero on failure.
cd /d "%~dp0.."
uv run python scripts/run_formatting_test_editor.py %*
