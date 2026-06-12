"""Shared pytest fixtures for FlowState tests."""

from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from formatting_harness import EditorTestDriver, open_editor_page


@pytest.fixture(scope="session")
def formatting_editor_driver():
    """Headless browser opened once for all formatting integration tests."""
    with sync_playwright() as playwright:
        browser, page = open_editor_page(playwright, headless=True)
        driver = EditorTestDriver(page)
        yield driver
        browser.close()


@pytest.fixture
def formatting_editor(formatting_editor_driver):
    """Reusable editor driver with a fresh page for each test."""
    formatting_editor_driver.reload_editor()
    yield formatting_editor_driver
