from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from core.config import settings
from db.elasticsearch import elastic_client
from utils.logger import logger
import asyncio
import time
from typing import Dict, List

class SeleniumService:
    def __init__(self):
        self._driver = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Remote WebDriver connected to Selenium Docker container"""
        chrome_options = Options()
        
        # Configure browser options
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Remote WebDriver configuration
        selenium_remote_url = settings.SELENIUM_REMOTE_URL
        
        try:
            self._driver = webdriver.Remote(
                command_executor=selenium_remote_url,
                options=chrome_options
            )
            self._driver.set_page_load_timeout(30)
            logger.info(f"Connected to Selenium Docker container at {selenium_remote_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Selenium Docker container: {e}")
            raise

    async def scrape_and_index(self, url: str, index_name: str = "web_content") -> Dict:
        """
        Scrape website content using Dockerized Selenium and index in Elasticsearch
        """
        try:
            loop = asyncio.get_event_loop()
            scraped_data = await loop.run_in_executor(
                None, 
                self._perform_scraping, 
                url
            )
            
            # Index in Elasticsearch
            es_response = await elastic_client.index(
                index=index_name,
                document=scraped_data
            )
            
            return {
                "data": scraped_data,
                "es_response": es_response
            }
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            raise

    def _perform_scraping(self, url: str) -> Dict:
        """Core scraping logic using Dockerized Selenium"""
        try:
            self._driver.get(url)
            
            # Wait for page load
            WebDriverWait(self._driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract content
            content = {
                "url": url,
                "title": self._driver.title,
                "content": self._driver.find_element(By.TAG_NAME, "body").text,
                "screenshot": self._take_screenshot(),
                "metadata": self._extract_metadata(),
                "timestamp": time.time()
            }
            
            return content
            
        except TimeoutException:
            logger.warning(f"Timeout occurred while loading {url}")
            return {"error": "Page load timeout"}
        finally:
            self._cleanup()

    def _extract_metadata(self) -> Dict:
        """Extract additional page metadata"""
        return {
            "headers": self._extract_headers(),
            "links": self._extract_links(),
            "scripts": self._extract_scripts(),
        }

    def _extract_links(self) -> List[str]:
        """Extract all links from the page"""
        return [link.get_attribute("href") for link in self._driver.find_elements(By.TAG_NAME, "a")]

    def _extract_scripts(self) -> List[str]:
        """Extract script sources"""
        return [script.get_attribute("src") for script in self._driver.find_elements(By.TAG_NAME, "script")]

    def _extract_headers(self) -> Dict:
        """Extract HTTP headers"""
        return self._driver.execute_script("return performance.getEntries()[0].response;")

    def _take_screenshot(self) -> str:
        """Take screenshot and return base64 encoded image"""
        return self._driver.get_screenshot_as_base64()

    def _cleanup(self):
        """Clean up browser resources"""
        try:
            self._driver.delete_all_cookies()
            self._driver.execute_script("window.localStorage.clear();")
            self._driver.execute_script("window.sessionStorage.clear();")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    async def search_indexed_content(self, query: str, index: str = "web_content") -> Dict:
        """Search scraped content in Elasticsearch"""
        try:
            response = await elastic_client.search(
                index=index,
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "content", "metadata.links"]
                        }
                    }
                }
            )
            return self._process_es_response(response)
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

    def _process_es_response(self, response: Dict) -> Dict:
        """Process Elasticsearch response"""
        return {
            "total": response["hits"]["total"]["value"],
            "results": [
                {
                    "score": hit["_score"],
                    **hit["_source"]
                } for hit in response["hits"]["hits"]
            ]
        }
    async def close(self):
            """Properly close the WebDriver session"""
            if self._driver:
                self._driver.quit()
                self._driver = None
                logger.info("Closed connection to Selenium Docker container")