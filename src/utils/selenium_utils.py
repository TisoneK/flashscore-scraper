from typing import List, Optional, Union, Tuple, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
import time
import logging
from src.config import CONFIG, SELECTORS

logger = logging.getLogger(__name__)

class SeleniumUtils:
    # Mapping of custom selector strings to Selenium By selectors
    SELECTOR_MAP = {
        "css": By.CSS_SELECTOR,
        "class": By.CLASS_NAME,
        "id": By.ID,
        "name": By.NAME,
        "tag": By.TAG_NAME,
        "link": By.LINK_TEXT,
        "partial_link": By.PARTIAL_LINK_TEXT,
        "xpath": By.XPATH
    }

    def __init__(self, driver: WebDriver):
        """Initialize with WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, CONFIG.timeout.element_timeout)
        self.logger = logging.getLogger(__name__)

    def selector(self, locator: str) -> By:
        """Get Selenium By locator strategy.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            
        Returns:
            By: Selenium By locator strategy
        """
        return self.SELECTOR_MAP.get(locator.lower(), By.CSS_SELECTOR)

    def hide(self, selector: str, value: str) -> bool:
        """
        Hide a single element using JavaScript.
        
        Args:
            selector: The selector type (css, class, id, xpath, etc.)
            value: The selector value
            
        Returns:
            bool: True if element was found and hidden, False otherwise
        """
        try:
            by = self.selector(selector)
            element = self.driver.find_element(by, value)
            self.driver.execute_script("arguments[0].style.display = 'none';", element)
            return True
        except (NoSuchElementException, ValueError) as e:
            if isinstance(e, ValueError):
                raise  # Re-raise ValueError for invalid selector types
            return False

    def hide_all(self, selector: str, value: str, duration: Optional[int] = None) -> int:
        """
        Hide all matching elements using JavaScript.
        
        Args:
            selector: The selector type (css, class, id, xpath, etc.)
            value: The selector value
            duration: Optional duration in seconds to keep checking for new elements
            
        Returns:
            int: Number of elements hidden
        """
        by = self.selector(selector)
        hidden_count = 0
        start_time = time.time()
        
        while True:
            elements = self.driver.find_elements(by, value)
            for element in elements:
                try:
                    self.driver.execute_script("arguments[0].style.display = 'none';", element)
                    hidden_count += 1
                except:
                    continue
            
            if duration is None or time.time() - start_time >= duration:
                break
            time.sleep(0.5)  # Small delay to prevent excessive CPU usage
            
        return hidden_count

    def find(self, locator: str, value: str, duration: int = None, parent: WebElement = None) -> Optional[WebElement]:
        """Find a single element.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            value: Locator value
            duration: Optional timeout duration
            parent: Optional parent element to search within
            
        Returns:
            Optional[WebElement]: Found element or None
        """
        try:
            by = self.selector(locator)
            if duration:
                wait = WebDriverWait(self.driver, duration)
                if parent:
                    return wait.until(EC.presence_of_element_located((by, value)), parent)
                return wait.until(EC.presence_of_element_located((by, value)))
            
            if parent:
                return parent.find_element(by, value)
            return self.driver.find_element(by, value)
            
        except Exception as e:
            self.logger.debug(f"Error finding element {locator}={value}: {e}")
            return None

    def find_all(self, locator: str, value: str, duration: int = None, parent: WebElement = None) -> List[WebElement]:
        """Find all elements matching the criteria.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            value: Locator value
            duration: Optional timeout duration
            parent: Optional parent element to search within
            
        Returns:
            List[WebElement]: List of found elements
        """
        try:
            by = self.selector(locator)
            if duration:
                wait = WebDriverWait(self.driver, duration)
                if parent:
                    return wait.until(EC.presence_of_all_elements_located((by, value)), parent)
                return wait.until(EC.presence_of_all_elements_located((by, value)))
            
            if parent:
                return parent.find_elements(by, value)
            return self.driver.find_elements(by, value)
            
        except Exception as e:
            self.logger.debug(f"Error finding elements {locator}={value}: {e}")
            return []

    def is_available(self, locator: str, value: str) -> bool:
        """Check if an element is available.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            value: Locator value
            
        Returns:
            bool: True if element is available, False otherwise
        """
        try:
            by = self.selector(locator)
            self.driver.find_element(by, value)
            return True
        except Exception:
            return False

    def count(self, selector: str, value: str, duration: Optional[int] = None) -> int:
        """
        Count the number of matching elements.
        
        Args:
            selector: The selector type (css, class, id, xpath, etc.)
            value: The selector value
            duration: Optional wait duration in seconds
            
        Returns:
            int: Number of matching elements
        """
        by = self.selector(selector)
        if duration:
            try:
                wait = WebDriverWait(self.driver, duration)
                wait.until(EC.presence_of_element_located((by, value)))
            except TimeoutException:
                return 0
        
        return len(self.driver.find_elements(by, value))

    def hide_common_banners(self) -> int:
        """
        Hide common banner elements that might appear on websites.
        
        Returns:
            int: Total number of elements hidden
        """
        banner_selectors = [
            ("id", "onetrust-consent-sdk"),
            ("class", "otPlaceholder"),
            ("id", "bannerExpander_13395"),
            ("xpath", "/html/body/div[contains(@class, 'banner')]"),
            ("xpath", "//div[contains(@class, 'cookie')]"),
            ("xpath", "//div[contains(@class, 'privacy')]"),
            ("xpath", "//div[contains(@class, 'advertisement')]"),
            ("xpath", "//div[contains(@class, 'popup')]"),
            ("xpath", "//div[contains(@class, 'modal')]"),
        ]
        
        total_hidden = 0
        for selector, value in banner_selectors:
            total_hidden += self.hide_all(selector=selector, value=value)
        
        return total_hidden

    def navigate_to(self, url: str) -> bool:
        """Navigate to a URL and wait for page load.
        
        Args:
            url: URL to navigate to
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for initial page load
            if not self.wait_for_page_load():
                return False
                
            # Wait for dynamic content
            if not self.wait_for_dynamic_content():
                return False
                
            # Additional wait for Flashscore's dynamic content
            time.sleep(2)  # Give extra time for dynamic content to load
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            return False

    def wait_for_dynamic_content(self, duration: Optional[int] = None) -> bool:
        """Wait for dynamic content to load.
        
        Args:
            duration: Optional timeout duration in seconds
            
        Returns:
            bool: True if content loaded successfully, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.dynamic_content_timeout)
            
            # First wait for document.readyState to be 'complete'
            def document_ready(driver):
                return driver.execute_script('return document.readyState') == 'complete'
            
            # Then wait for network to be idle (no pending requests)
            def network_idle(driver):
                return driver.execute_script('''
                    return window.performance.getEntriesByType('resource')
                        .filter(r => r.responseEnd === 0).length === 0;
                ''')
            
            # Wait for both conditions
            wait.until(document_ready)
            wait.until(network_idle)
            
            # Additional wait for Flashscore's dynamic content
            time.sleep(1)  # Small delay to ensure dynamic content is rendered
            
            return True
            
        except TimeoutException:
            self.logger.error("Timeout waiting for dynamic content")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for dynamic content: {e}")
            return False

    def parse_matches(self) -> List['Match']:
        """Parse matches from the current page.
        
        Returns:
            List[Match]: List of parsed matches
        """
        from .parser import MatchParser
        parser = MatchParser(self.driver.page_source)
        return parser.get_matches()

    def close(self) -> None:
        """Close the WebDriver instance."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def wait_for_element(self, locator: str, value: str, duration: int = None, parent: WebElement = None) -> bool:
        """Wait for an element to be present.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            value: Locator value
            duration: Optional timeout duration
            parent: Optional parent element to search within
            
        Returns:
            bool: True if element is found, False otherwise
        """
        try:
            by = self.selector(locator)
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            
            if parent:
                # Create a custom condition for finding element within parent
                def element_in_parent(driver):
                    try:
                        return parent.find_element(by, value)
                    except:
                        return None
                element = wait.until(element_in_parent)
                return element is not None
            else:
                element = wait.until(EC.presence_of_element_located((by, value)))
                return element is not None
            
        except Exception as e:
            self.logger.debug(f"Error waiting for element {locator}={value}: {e}")
            return False

    def wait_for_elements(self, locator: str, value: str, duration: int = None) -> bool:
        """Wait for elements to be present.
        
        Args:
            locator: Locator strategy (css, xpath, class, id)
            value: Locator value
            duration: Optional timeout duration
            
        Returns:
            bool: True if elements are present, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            wait.until(EC.presence_of_all_elements_located((self.selector(locator), value)))
            return True
        except Exception as e:
            self.logger.debug(f"Error waiting for elements {locator}={value}: {e}")
            return False

    def wait_for_element_to_disappear(self, by: str, value: str, duration: Optional[int] = None) -> bool:
        """Wait for an element to disappear.
        
        Args:
            by: Locator strategy (e.g., "id", "class", "css")
            value: Locator value
            duration: Optional timeout duration in seconds
            
        Returns:
            bool: True if element disappeared, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            if by == "class":
                wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, value)))
            elif by == "id":
                wait.until(EC.invisibility_of_element_located((By.ID, value)))
            elif by == "css":
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, value)))
            return True
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for element to disappear: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for element to disappear {by}={value}: {e}")
            return False

    def wait_for_elements_to_disappear(self, by: str, value: str, duration: Optional[int] = None) -> bool:
        """Wait for elements to disappear.
        
        Args:
            by: Locator strategy (e.g., "id", "class", "css")
            value: Locator value
            duration: Optional timeout duration in seconds
            
        Returns:
            bool: True if elements disappeared, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            if by == "class":
                wait.until(EC.invisibility_of_all_elements_located((By.CLASS_NAME, value)))
            elif by == "id":
                wait.until(EC.invisibility_of_all_elements_located((By.ID, value)))
            elif by == "css":
                wait.until(EC.invisibility_of_all_elements_located((By.CSS_SELECTOR, value)))
            return True
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for elements to disappear: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for elements to disappear {by}={value}: {e}")
            return False

    def wait_for_element_to_be_clickable(self, by: str, value: str, duration: Optional[int] = None) -> bool:
        """Wait for an element to be clickable.
        
        Args:
            by: Locator strategy (e.g., "id", "class", "css")
            value: Locator value
            duration: Optional timeout duration in seconds
            
        Returns:
            bool: True if element is clickable, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            if by == "class":
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, value)))
            elif by == "id":
                wait.until(EC.element_to_be_clickable((By.ID, value)))
            elif by == "css":
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, value)))
            return True
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for element to be clickable: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for element to be clickable {by}={value}: {e}")
            return False

    def wait_for_elements_to_be_clickable(self, by: str, value: str, duration: Optional[int] = None) -> bool:
        """Wait for elements to be clickable.
        
        Args:
            by: Locator strategy (e.g., "id", "class", "css")
            value: Locator value
            duration: Optional timeout duration in seconds
            
        Returns:
            bool: True if elements are clickable, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, duration or CONFIG.timeout.element_timeout)
            if by == "class":
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, value)))
            elif by == "id":
                wait.until(EC.element_to_be_clickable((By.ID, value)))
            elif by == "css":
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, value)))
            return True
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for elements to be clickable: {by}={value}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for elements to be clickable {by}={value}: {e}")
            return False

    def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """Wait for the page to load completely.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        try:
            timeout = timeout or CONFIG.timeout.page_load_timeout
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            return True
        except TimeoutException:
            self.logger.warning(f"Page load timeout after {timeout} seconds")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for page load: {e}")
            return False 