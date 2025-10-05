"""
Base web scraper class using Playwright for browser automation.

This module provides a base class for web scraping with Playwright,
including browser management, page navigation, element extraction,
and error handling.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Error
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from config.settings import (
    ORANGE_COUNTY_SCRAPER,
    RATE_LIMITS,
    COMPLIANCE_CONFIG,
    RAW_DATA_DIR,
)
from config.selectors import is_xpath
from src.utils import get_logger, Timer


class WebScraperBase:
    """Base class for web scraping with Playwright."""

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        timeout: int = 30000,
    ):
        """
        Initialize the web scraper.

        Args:
            headless: Run browser in headless mode
            browser_type: Browser type (chromium, firefox, webkit)
            timeout: Default timeout in milliseconds
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install with: pip install playwright && playwright install"
            )

        self.logger = get_logger(__name__)
        self.headless = headless
        self.browser_type = browser_type
        self.timeout = timeout

        # Rate limiting
        self.delay = RATE_LIMITS["scraper_delay"]

        # Compliance
        self.user_agent = COMPLIANCE_CONFIG["user_agent"]

        # Browser components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Statistics
        self.stats = {
            "pages_visited": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_records": 0,
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def start(self):
        """Start the browser instance."""
        try:
            self.logger.info(f"Starting {self.browser_type} browser (headless={self.headless})")

            # Start Playwright
            self.playwright = sync_playwright().start()

            # Get browser type
            browser_launcher = getattr(self.playwright, self.browser_type)

            # Launch browser
            self.browser = browser_launcher.launch(headless=self.headless)

            # Create context with custom user agent
            self.context = self.browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080},
            )

            # Set default timeout
            self.context.set_default_timeout(self.timeout)

            # Create page
            self.page = self.context.new_page()

            self.logger.info("Browser started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise

    def navigate(self, url: str, wait_for: Optional[str] = None) -> bool:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_for: Optional selector to wait for after navigation

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            self.logger.debug(f"Navigating to: {url}")

            # Navigate to URL
            response = self.page.goto(url, wait_until="domcontentloaded")

            # Check response status
            if response and response.status >= 400:
                self.logger.warning(f"HTTP {response.status} for {url}")
                return False

            # Wait for specific selector if provided
            if wait_for:
                self.wait_for_selector(wait_for)

            self.stats["pages_visited"] += 1

            # Apply rate limiting
            if self.delay > 0:
                self.logger.debug(f"Rate limiting: waiting {self.delay} seconds")
                time.sleep(self.delay)

            return True

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False

    def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None,
        state: str = "visible"
    ) -> bool:
        """
        Wait for a selector to appear.

        Args:
            selector: CSS selector or XPath
            timeout: Timeout in milliseconds (default: use instance timeout)
            state: State to wait for (visible, attached, hidden, detached)

        Returns:
            True if element found, False otherwise
        """
        try:
            timeout_ms = timeout if timeout is not None else self.timeout

            if is_xpath(selector):
                self.page.wait_for_selector(
                    f"xpath={selector}",
                    timeout=timeout_ms,
                    state=state
                )
            else:
                self.page.wait_for_selector(
                    selector,
                    timeout=timeout_ms,
                    state=state
                )

            return True

        except Exception as e:
            self.logger.debug(f"Selector not found: {selector} ({e})")
            return False

    def extract_text(
        self,
        selectors: Union[str, List[str]],
        default: str = ""
    ) -> str:
        """
        Extract text from element using selectors.

        Args:
            selectors: Single selector or list of selectors to try
            default: Default value if extraction fails

        Returns:
            Extracted text or default value
        """
        # Ensure selectors is a list
        if isinstance(selectors, str):
            selectors = [selectors]

        # Try each selector
        for selector in selectors:
            try:
                if is_xpath(selector):
                    element = self.page.query_selector(f"xpath={selector}")
                else:
                    element = self.page.query_selector(selector)

                if element:
                    text = element.inner_text().strip()
                    if text:
                        return text

            except Exception as e:
                self.logger.debug(f"Failed to extract with selector '{selector}': {e}")
                continue

        # All selectors failed
        self.logger.debug(f"No text found for selectors: {selectors}")
        return default

    def extract_attribute(
        self,
        selectors: Union[str, List[str]],
        attribute: str,
        default: str = ""
    ) -> str:
        """
        Extract attribute from element using selectors.

        Args:
            selectors: Single selector or list of selectors to try
            attribute: Attribute name to extract
            default: Default value if extraction fails

        Returns:
            Extracted attribute value or default value
        """
        # Ensure selectors is a list
        if isinstance(selectors, str):
            selectors = [selectors]

        # Try each selector
        for selector in selectors:
            try:
                if is_xpath(selector):
                    element = self.page.query_selector(f"xpath={selector}")
                else:
                    element = self.page.query_selector(selector)

                if element:
                    attr_value = element.get_attribute(attribute)
                    if attr_value:
                        return attr_value.strip()

            except Exception as e:
                self.logger.debug(f"Failed to extract attribute with selector '{selector}': {e}")
                continue

        # All selectors failed
        self.logger.debug(f"No attribute '{attribute}' found for selectors: {selectors}")
        return default

    def click(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Click an element.

        Args:
            selector: CSS selector or XPath
            timeout: Timeout in milliseconds

        Returns:
            True if click successful, False otherwise
        """
        try:
            timeout_ms = timeout if timeout is not None else self.timeout

            if is_xpath(selector):
                self.page.click(f"xpath={selector}", timeout=timeout_ms)
            else:
                self.page.click(selector, timeout=timeout_ms)

            return True

        except Exception as e:
            self.logger.error(f"Click failed for selector '{selector}': {e}")
            return False

    def fill_input(self, selector: str, value: str, timeout: Optional[int] = None) -> bool:
        """
        Fill an input field.

        Args:
            selector: CSS selector or XPath
            value: Value to fill
            timeout: Timeout in milliseconds

        Returns:
            True if fill successful, False otherwise
        """
        try:
            timeout_ms = timeout if timeout is not None else self.timeout

            if is_xpath(selector):
                self.page.fill(f"xpath={selector}", value, timeout=timeout_ms)
            else:
                self.page.fill(selector, value, timeout=timeout_ms)

            return True

        except Exception as e:
            self.logger.error(f"Fill failed for selector '{selector}': {e}")
            return False

    def screenshot(self, filepath: Union[str, Path], full_page: bool = False) -> bool:
        """
        Take a screenshot.

        Args:
            filepath: Path to save screenshot
            full_page: Capture full page or just viewport

        Returns:
            True if screenshot successful, False otherwise
        """
        try:
            self.page.screenshot(path=str(filepath), full_page=full_page)
            self.logger.info(f"Screenshot saved to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return False

    def get_html(self) -> str:
        """
        Get current page HTML.

        Returns:
            HTML content as string
        """
        try:
            return self.page.content()
        except Exception as e:
            self.logger.error(f"Failed to get HTML: {e}")
            return ""

    def save_html(self, filepath: Union[str, Path]) -> bool:
        """
        Save current page HTML to file.

        Args:
            filepath: Path to save HTML

        Returns:
            True if save successful, False otherwise
        """
        try:
            html = self.get_html()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)

            self.logger.info(f"HTML saved to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save HTML: {e}")
            return False

    def check_element_exists(self, selector: str) -> bool:
        """
        Check if element exists on page.

        Args:
            selector: CSS selector or XPath

        Returns:
            True if element exists, False otherwise
        """
        try:
            if is_xpath(selector):
                element = self.page.query_selector(f"xpath={selector}")
            else:
                element = self.page.query_selector(selector)

            return element is not None

        except Exception as e:
            self.logger.debug(f"Error checking element existence: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """
        Get scraper statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics counters."""
        self.stats = {
            "pages_visited": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_records": 0,
        }

    def close(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
                self.logger.debug("Page closed")

            if self.context:
                self.context.close()
                self.logger.debug("Context closed")

            if self.browser:
                self.browser.close()
                self.logger.debug("Browser closed")

            if self.playwright:
                self.playwright.stop()
                self.logger.debug("Playwright stopped")

            self.logger.info("Browser cleanup complete")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
