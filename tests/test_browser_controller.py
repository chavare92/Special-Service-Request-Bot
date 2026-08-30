"""Unit tests for portal navigation helpers (no live browser)."""
from app.browser_controller import is_aspnet_error_page, form_button_matches, is_portal_success_message
from app.config import ELOGIPARK_SSR_URL, ELOGIPARK_SSR_ADD_URL


def test_ssr_url_points_at_ssinvoice():
    assert "Commercial/SSInvoice.aspx" in ELOGIPARK_SSR_URL
    assert ELOGIPARK_SSR_ADD_URL == ELOGIPARK_SSR_URL
    assert "SpecialServiceAdd.aspx" not in ELOGIPARK_SSR_URL
    assert "/Finance/" not in ELOGIPARK_SSR_URL


def test_aspnet_404_is_detected():
    title = "The resource cannot be found."
    body = "Server Error in '/elogipark' Application. HTTP 404. Requested URL: /elogipark/Finance/SpecialServiceAdd.aspx"
    assert is_aspnet_error_page(title, body) is True


def test_normal_ssinvoice_title_is_not_error():
    assert is_aspnet_error_page("eLOGiPark :: Special Service Invoice", "Doc Type Booking No.") is False


def test_format_exception_page_is_detected():
    title = "Input string was not in a correct format."
    body = "Server Error in '/elogipark' Application. Conversion from string \"\" to type 'Double'"
    assert is_aspnet_error_page(title, body) is True


def test_saved_successfully_is_success_not_error():
    assert is_portal_success_message("Saved Successfully") is True
    assert is_portal_success_message("Checked Invoice Check Box") is False
    assert is_portal_success_message("") is False


def test_form_button_matches_uppercase_add():
    assert form_button_matches("ADD", "", ["ADD", "Add"]) is True
    assert form_button_matches("Add", "", ["ADD", "Add"]) is True
    assert form_button_matches("Exit", "", ["ADD", "Add"]) is False
    assert form_button_matches("", "SAVE", ["SAVE", "Save"]) is True
