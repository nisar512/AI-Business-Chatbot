from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

def _init_driver(self):
    """Connect to Dockerized Selenium container via RemoteWebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Proxy settings if needed
    if settings.SELENIUM_PROXY:
        chrome_options.add_argument(f"--proxy-server={settings.SELENIUM_PROXY}")

    try:
        self._driver: RemoteWebDriver = webdriver.Remote(
            command_executor=settings.SELENIUM_REMOTE_URL,
            options=chrome_options
        )
        self._driver.set_page_load_timeout(30)
    except WebDriverException as e:
        logger.error(f"Remote WebDriver initialization failed: {e}")
        raise
