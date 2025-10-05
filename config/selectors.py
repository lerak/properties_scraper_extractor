"""
CSS and XPath selectors for web scraping Orange County property data.

This module contains all selectors used to extract property information
from the Orange County Tax Assessor website.
"""

# =======================
# Orange County Selectors
# =======================

ORANGE_COUNTY_SELECTORS = {
    # Search Form Selectors
    "search_form": {
        "owner_name_input": 'input[name="Query.OwnerName"]',
        "parcel_id_input": 'input[name="Query.AccountNumber"]',
        "address_input": 'input[name="Query.PropertyLocation"]',
        "search_button": '#btn-search-submit',
        "submit_button": 'button[type="submit"]',
    },

    # Search Results Table
    "results_table": {
        "table": "table.search-results",
        "table_alt": "table#property-results",
        "rows": "table.search-results tbody tr",
        "rows_alt": "table#property-results tbody tr",
        "no_results": "div.no-results",
        "no_results_alt": "p:contains('No results found')",
    },

    # Property Detail Page
    "property_details": {
        # Owner Information
        "owner_name": [
            "div.owner-info h3",
            "span.owner-name",
            "td:contains('Owner Name') + td",
            "//label[contains(text(), 'Owner')]/following-sibling::span",
        ],

        # Parcel Information
        "parcel_id": [
            "span.parcel-id",
            "td:contains('Parcel ID') + td",
            "div.parcel-number",
            "//label[contains(text(), 'Parcel')]/following-sibling::span",
        ],

        # Property Address
        "property_address": [
            "div.property-address",
            "span.address",
            "td:contains('Property Address') + td",
            "//label[contains(text(), 'Property Address')]/following-sibling::span",
        ],

        # Mailing Address
        "mailing_address": [
            "div.mailing-address",
            "span.mailing",
            "td:contains('Mailing Address') + td",
            "//label[contains(text(), 'Mailing Address')]/following-sibling::span",
        ],

        # City
        "city": [
            "span.city",
            "td:contains('City') + td",
            "//label[contains(text(), 'City')]/following-sibling::span",
        ],

        # State
        "state": [
            "span.state",
            "td:contains('State') + td",
            "//label[contains(text(), 'State')]/following-sibling::span",
        ],

        # ZIP Code
        "zip_code": [
            "span.zip",
            "span.zipcode",
            "td:contains('ZIP') + td",
            "td:contains('Zip Code') + td",
            "//label[contains(text(), 'ZIP')]/following-sibling::span",
        ],

        # County
        "county": [
            "span.county",
            "td:contains('County') + td",
            "//label[contains(text(), 'County')]/following-sibling::span",
        ],

        # Assessed Value
        "assessed_value": [
            "span.assessed-value",
            "td:contains('Assessed Value') + td",
            "td:contains('Total Value') + td",
            "//label[contains(text(), 'Assessed Value')]/following-sibling::span",
        ],

        # Sale Date
        "sale_date": [
            "span.sale-date",
            "td:contains('Sale Date') + td",
            "td:contains('Last Sale Date') + td",
            "//label[contains(text(), 'Sale Date')]/following-sibling::span",
        ],

        # Sale Price
        "sale_price": [
            "span.sale-price",
            "td:contains('Sale Price') + td",
            "td:contains('Last Sale Price') + td",
            "//label[contains(text(), 'Sale Price')]/following-sibling::span",
        ],
    },

    # Pagination
    "pagination": {
        "next_page": [
            "a.next-page",
            "a:contains('Next')",
            "button.pagination-next",
            "//a[contains(text(), 'Next')]",
        ],
        "prev_page": [
            "a.prev-page",
            "a:contains('Previous')",
            "button.pagination-prev",
        ],
        "page_numbers": "ul.pagination li a",
        "current_page": "ul.pagination li.active",
    },

    # Loading Indicators
    "loading": {
        "spinner": [
            "div.spinner",
            "div.loading",
            "img[alt='Loading']",
        ],
        "overlay": "div.loading-overlay",
    },

    # Error Messages
    "errors": {
        "error_message": [
            "div.error",
            "div.alert-danger",
            "p.error-text",
            "span.error-message",
        ],
        "validation_error": "span.validation-error",
    },
}

# =======================
# Alternative Selectors (Fallbacks)
# =======================

# If primary selectors fail, try these alternative patterns
FALLBACK_SELECTORS = {
    "owner_name": [
        "//tr[td[contains(text(), 'Owner')]]/td[2]",
        "//div[contains(@class, 'owner')]//text()",
    ],
    "parcel_id": [
        "//tr[td[contains(text(), 'Parcel')]]/td[2]",
        "//div[contains(@class, 'parcel')]//text()",
    ],
    "property_address": [
        "//tr[td[contains(text(), 'Property Address')]]/td[2]",
        "//tr[td[contains(text(), 'Site Address')]]/td[2]",
    ],
    "assessed_value": [
        "//tr[td[contains(text(), 'Total')]]/td[2]",
        "//tr[td[contains(text(), 'Value')]]/td[2]",
    ],
}

# =======================
# Selector Utilities
# =======================

def get_selector(field_name: str, selector_type: str = "property_details") -> list:
    """
    Retrieve selectors for a specific field.

    Args:
        field_name: Name of the field (e.g., 'owner_name', 'parcel_id')
        selector_type: Type of selector ('property_details', 'search_form', etc.)

    Returns:
        List of selectors to try in order
    """
    selectors = ORANGE_COUNTY_SELECTORS.get(selector_type, {}).get(field_name, [])

    # Ensure selectors is always a list
    if isinstance(selectors, str):
        selectors = [selectors]

    # Add fallback selectors if available
    if field_name in FALLBACK_SELECTORS:
        selectors.extend(FALLBACK_SELECTORS[field_name])

    return selectors


def is_xpath(selector: str) -> bool:
    """
    Determine if a selector is XPath or CSS.

    Args:
        selector: The selector string

    Returns:
        True if XPath, False if CSS
    """
    return selector.startswith("//") or selector.startswith("(")
