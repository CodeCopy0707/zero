"""
Browser automation tools for Agent Zero Gemini
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64

from core.tools import BaseTool

logger = logging.getLogger(__name__)

class BrowserTool(BaseTool):
    """Browser automation tool using Selenium"""
    
    def __init__(self):
        super().__init__(
            name="browser_automation",
            description="Automate web browser interactions, navigate pages, fill forms, click elements"
        )
        self.driver = None
        self._setup_browser()
    
    def _setup_browser(self):
        """Setup browser driver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.webdriver = webdriver
            self.By = By
            self.WebDriverWait = WebDriverWait
            self.EC = EC
            
            # Chrome options
            self.chrome_options = Options()
            self.chrome_options.add_argument("--headless")
            self.chrome_options.add_argument("--no-sandbox")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--window-size=1920,1080")
            
        except ImportError:
            logger.warning("Selenium not installed. Browser automation will not be available.")
            self.webdriver = None
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute browser action"""
        if not self.webdriver:
            return {
                "success": False,
                "error": "Selenium not available. Install with: pip install selenium"
            }
        
        try:
            if action == "navigate":
                return await self._navigate(kwargs.get("url"))
            elif action == "click":
                return await self._click(kwargs.get("selector"))
            elif action == "type":
                return await self._type(kwargs.get("selector"), kwargs.get("text"))
            elif action == "get_text":
                return await self._get_text(kwargs.get("selector"))
            elif action == "screenshot":
                return await self._screenshot(kwargs.get("filename"))
            elif action == "wait_for_element":
                return await self._wait_for_element(kwargs.get("selector"), kwargs.get("timeout", 10))
            elif action == "execute_script":
                return await self._execute_script(kwargs.get("script"))
            elif action == "get_page_source":
                return await self._get_page_source()
            elif action == "close":
                return await self._close_browser()
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _ensure_driver(self):
        """Ensure browser driver is initialized"""
        if not self.driver:
            self.driver = self.webdriver.Chrome(options=self.chrome_options)
    
    async def _navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL"""
        await self._ensure_driver()
        
        await asyncio.to_thread(self.driver.get, url)
        
        return {
            "success": True,
            "url": self.driver.current_url,
            "title": self.driver.title
        }
    
    async def _click(self, selector: str) -> Dict[str, Any]:
        """Click element by selector"""
        await self._ensure_driver()
        
        element = self.driver.find_element(self.By.CSS_SELECTOR, selector)
        await asyncio.to_thread(element.click)
        
        return {
            "success": True,
            "message": f"Clicked element: {selector}"
        }
    
    async def _type(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element"""
        await self._ensure_driver()
        
        element = self.driver.find_element(self.By.CSS_SELECTOR, selector)
        await asyncio.to_thread(element.clear)
        await asyncio.to_thread(element.send_keys, text)
        
        return {
            "success": True,
            "message": f"Typed text into {selector}"
        }
    
    async def _get_text(self, selector: str) -> Dict[str, Any]:
        """Get text from element"""
        await self._ensure_driver()
        
        element = self.driver.find_element(self.By.CSS_SELECTOR, selector)
        text = element.text
        
        return {
            "success": True,
            "text": text
        }
    
    async def _screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take screenshot"""
        await self._ensure_driver()
        
        if not filename:
            filename = f"screenshot_{asyncio.get_event_loop().time()}.png"
        
        screenshot_path = Path("tmp") / filename
        screenshot_path.parent.mkdir(exist_ok=True)
        
        await asyncio.to_thread(self.driver.save_screenshot, str(screenshot_path))
        
        return {
            "success": True,
            "filename": str(screenshot_path),
            "message": f"Screenshot saved to {screenshot_path}"
        }
    
    async def _wait_for_element(self, selector: str, timeout: int = 10) -> Dict[str, Any]:
        """Wait for element to be present"""
        await self._ensure_driver()
        
        wait = self.WebDriverWait(self.driver, timeout)
        element = await asyncio.to_thread(
            wait.until,
            self.EC.presence_of_element_located((self.By.CSS_SELECTOR, selector))
        )
        
        return {
            "success": True,
            "message": f"Element found: {selector}"
        }
    
    async def _execute_script(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript"""
        await self._ensure_driver()
        
        result = await asyncio.to_thread(self.driver.execute_script, script)
        
        return {
            "success": True,
            "result": result
        }
    
    async def _get_page_source(self) -> Dict[str, Any]:
        """Get page source"""
        await self._ensure_driver()
        
        source = self.driver.page_source
        
        return {
            "success": True,
            "source": source
        }
    
    async def _close_browser(self) -> Dict[str, Any]:
        """Close browser"""
        if self.driver:
            await asyncio.to_thread(self.driver.quit)
            self.driver = None
        
        return {
            "success": True,
            "message": "Browser closed"
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Browser action to perform",
                "enum": ["navigate", "click", "type", "get_text", "screenshot", "wait_for_element", "execute_script", "get_page_source", "close"]
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to (for navigate action)"
            },
            "selector": {
                "type": "string", 
                "description": "CSS selector for element (for click, type, get_text, wait_for_element actions)"
            },
            "text": {
                "type": "string",
                "description": "Text to type (for type action)"
            },
            "filename": {
                "type": "string",
                "description": "Screenshot filename (for screenshot action)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (for wait_for_element action)",
                "default": 10
            },
            "script": {
                "type": "string",
                "description": "JavaScript code to execute (for execute_script action)"
            }
        }

class WebScrapingTool(BaseTool):
    """Web scraping tool with BeautifulSoup"""
    
    def __init__(self):
        super().__init__(
            name="web_scraping",
            description="Extract data from web pages using CSS selectors and XPath"
        )
    
    async def execute(self, url: str, selectors: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """Scrape web page"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Get page content
            headers = kwargs.get("headers", {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            response = await asyncio.to_thread(requests.get, url, headers=headers)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract data using selectors
            extracted_data = {}
            for key, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        extracted_data[key] = elements[0].get_text(strip=True)
                    else:
                        extracted_data[key] = [elem.get_text(strip=True) for elem in elements]
                else:
                    extracted_data[key] = None
            
            return {
                "success": True,
                "url": url,
                "data": extracted_data,
                "page_title": soup.title.string if soup.title else None
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "Required packages not installed. Install with: pip install requests beautifulsoup4"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "url": {
                "type": "string",
                "description": "URL to scrape"
            },
            "selectors": {
                "type": "object",
                "description": "Dictionary of CSS selectors to extract data",
                "example": {"title": "h1", "links": "a[href]"}
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers to send with request",
                "optional": True
            }
        }
