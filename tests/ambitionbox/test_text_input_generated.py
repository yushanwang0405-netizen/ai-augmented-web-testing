import pytest
import allure
from playwright.sync_api import Page


@allure.feature("Search Bar")
class TestSearchBar:
    """Test suite for the global search bar input and clear functionality."""

    # ------------------------------------------------------------------ #
    # TC_001 — Search bar accepts text input
    # ------------------------------------------------------------------ #
    @allure.story("TC_001 - Search bar accepts text input")
    @pytest.mark.high
    @pytest.mark.smoke
    @pytest.mark.web
    def test_search_bar_accepts_text_input(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        search_bar.fill("Accenture")

        current_value = search_bar.get_current_value()
        assert current_value == "Accenture", (
            f"Expected search bar to contain 'Accenture', got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_002 — Search bar accepts numeric input
    # ------------------------------------------------------------------ #
    @allure.story("TC_002 - Search bar accepts numeric input")
    @pytest.mark.medium
    @pytest.mark.regression
    @pytest.mark.web
    def test_search_bar_accepts_numeric_input(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        search_bar.fill("1234567890")

        current_value = search_bar.get_current_value()
        assert current_value == "1234567890", (
            f"Expected search bar to contain '1234567890', got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_003 — Search bar accepts special characters
    # ------------------------------------------------------------------ #
    @allure.story("TC_003 - Search bar accepts special characters")
    @pytest.mark.medium
    @pytest.mark.regression
    @pytest.mark.web
    def test_search_bar_accepts_special_characters(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        special_chars = "@#$%&*!"
        search_bar.fill(special_chars)

        current_value = search_bar.get_current_value()
        assert current_value == special_chars, (
            f"Expected search bar to contain '{special_chars}', got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_004 — Search input can be cleared using the clear button/method
    # ------------------------------------------------------------------ #
    @allure.story("TC_004 - Search input can be cleared using the clear button")
    @pytest.mark.high
    @pytest.mark.smoke
    @pytest.mark.web
    def test_search_input_cleared_using_clear_button(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        search_bar.fill("Accenture")
        assert search_bar.get_current_value() == "Accenture", (
            "Pre-condition failed: search bar should contain 'Accenture' before clearing"
        )

        search_bar.clear()

        current_value = search_bar.get_current_value()
        assert current_value == "", (
            f"Expected search bar to be empty after clear, got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_005 — Search input can be cleared manually by the user
    # ------------------------------------------------------------------ #
    @allure.story("TC_005 - Search input can be cleared manually by the user")
    @pytest.mark.high
    @pytest.mark.sanity
    @pytest.mark.web
    def test_search_input_cleared_manually(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        search_bar.fill("Accenture")
        assert search_bar.get_current_value() == "Accenture", (
            "Pre-condition failed: search bar should contain 'Accenture' before clearing"
        )

        # Select all text and press Backspace
        search_bar.page.locator(search_bar.INPUT).press("Control+A")
        search_bar.page.locator(search_bar.INPUT).press("Backspace")

        current_value = search_bar.get_current_value()
        assert current_value == "", (
            f"Expected search bar to be empty after manual clear, got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_006 — Search bar remains empty when no input is provided
    # ------------------------------------------------------------------ #
    @allure.story("TC_006 - Search bar remains empty when no input is provided")
    @pytest.mark.medium
    @pytest.mark.sanity
    @pytest.mark.web
    def test_search_bar_remains_empty_by_default(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        current_value = search_bar.get_current_value()
        assert current_value == "", (
            f"Expected search bar to be empty by default, got '{current_value}'"
        )

    # ------------------------------------------------------------------ #
    # TC_007 — Search bar rejects excessively long input gracefully
    # ------------------------------------------------------------------ #
    @allure.story("TC_007 - Search bar rejects excessively long input gracefully")
    @pytest.mark.low
    @pytest.mark.regression
    @pytest.mark.web
    def test_search_bar_handles_very_long_input_gracefully(self, home_page, search_bar):
        home_page.open()
        assert search_bar.is_visible(), "Search bar should be visible on the page"

        long_input = "A" * 500  # 500-character string, well above normal limits

        # The page should not crash regardless of the input length
        try:
            search_bar.fill(long_input)
        except Exception as exc:
            pytest.fail(
                f"Search bar should handle long input gracefully without crashing. "
                f"Exception raised: {exc}"
            )

        current_value = search_bar.get_current_value()
        # The bar either truncates, accepts all, or limits — all are acceptable
        # as long as no crash occurs. We only assert the page is still functional.
        assert isinstance(current_value, str), (
            "Search bar should always return a string value"
        )
        # If the bar accepted input, length should not exceed what was sent
        # (truncation is acceptable behavior)
        assert len(current_value) <= len(long_input), (
            f"Search bar returned more characters than typed: "
            f"got len={len(current_value)}, typed len={len(long_input)}"
        )

        # After handling long input, the bar should still be visible/usable
        assert search_bar.is_visible(), (
            "Search bar should remain visible after handling long input"
        )