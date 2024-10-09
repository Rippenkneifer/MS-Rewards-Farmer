import argparse
import logging
import random
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Type
import os
import ipapi
import undetected_chromedriver as webdriver
from ipapi.exceptions import RateLimited
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src import Account, RemainingSearches
from src.userAgentGenerator import GenerateUserAgent
from src.utils import Utils


class Browser:
    """WebDriver wrapper class."""

    webdriver: webdriver.Chrome

    def __init__(
        self, mobile: bool, account: Account, args: argparse.Namespace
    ) -> None:
        logging.debug("in __init__")
        self.mobile = mobile
        self.browserType = "mobile" if mobile else "desktop"
        self.headless = not args.visible
        self.username = account.username
        self.password = account.password
        self.totp = account.totp
        self.localeLang, self.localeGeo = self.getCCodeLang(args.lang, args.geo)
        self.proxy = None
        if args.proxy:
            self.proxy = args.proxy
        elif account.proxy:
            self.proxy = account.proxy
        self.userDataDir = self.setupProfiles()
        self.browserConfig = Utils.getBrowserConfig(self.userDataDir)
        (
            self.userAgent,
            self.userAgentMetadata,
            newBrowserConfig,
        ) = GenerateUserAgent().userAgent(self.browserConfig, mobile)
        if newBrowserConfig:
            self.browserConfig = newBrowserConfig
            Utils.saveBrowserConfig(self.userDataDir, self.browserConfig)
        self.webdriver = self.browserSetup()
        self.utils = Utils(self.webdriver)
        logging.debug("out __init__")
        self.log_headers()

    def human_interactions(self, driver):
        actions = ActionChains(driver)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            logging.error(f"Error while waiting for the page to load: {e}")
            return
        current_url = driver.current_url
        if "bing.com" not in current_url:
            logging.info(f"Skipping mouse movements. Current URL does not contain 'bing.com': {current_url}")
            return
        logging.info(f"Executing mouse movements. Current URL: {current_url}")
        window_size = driver.get_window_size()
        window_position = driver.get_window_position()
        window_width = window_size['width']
        window_height = window_size['height']
        window_x = window_position['x']
        window_y = window_position['y']
        logging.info(f"Window width: {window_width}, height: {window_height}, position x: {window_x}, y: {window_y}")
        for _ in range(random.randint(5, 15)):
            x_target = random.randint(0, window_width - 1)
            y_target = random.randint(0, window_height - 1)
            logging.info(f"Moving mouse to x: {x_target}, y: {y_target}")
            steps = 10
            x_current, y_current = 0, 0
            try:
                for i in range(steps):
                    x_step = (x_target - x_current) / steps
                    y_step = (y_target - y_current) / steps
                    actions.move_by_offset(x_step, y_step).perform()
                    x_current += x_step
                    y_current += y_step
                    time.sleep(0.05)
            except Exception as e:
                logging.error(f"Error during mouse movement: {e}")
            time.sleep(random.uniform(0.3, 0.75))

    def __enter__(self):
        logging.debug("in __enter__")
        return self

    def __exit__(self, exc_type: Type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None):
        logging.debug(f"in __exit__ exc_type={exc_type} exc_value={exc_value} traceback={traceback}")
        try:
            self.webdriver.quit()
        except Exception as e:
            logging.error(f"Error during browser shutdown: {e}")

    def log_headers(self):
        """Logs the current User-Agent and Headers being used by the browser."""
        logging.info(f"Current User-Agent: {self.userAgent}")
        if self.proxy:
            logging.info(f"Using Proxy: {self.proxy}")

    def browserSetup(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.headless = self.headless
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument(f"--lang={self.localeLang}")
        options.add_argument("--log-level=3")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--no-sandbox")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--start-minimized")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--force-dark-mode")
        options.add_argument("--window-position=10000,100")  

        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        version = self.getChromeVersion()
        major = int(version.split(".")[0])

        try:
            driver = webdriver.Chrome(
                options=options,
                user_data_dir=self.userDataDir.as_posix(),
                version_main=major,
            )
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {e}")
            raise

        # Enhanced Anti-Bot Measures
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                // Delete webdriver property to hide automation
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Add fake plugin data to mimic a real user
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Viewer'},
                        {name: 'Google Native Client'},
                        {name: 'Widevine Content Decryption Module'}
                    ]
                });

                // Set language properties to mimic real settings
                Object.defineProperty(navigator, 'languages', {get: () => ['de-DE', 'de']});
                Object.defineProperty(navigator, 'language', {get: () => 'de-DE'});

                // Mimic the presence of the Chrome object
                Object.defineProperty(window, 'chrome', {get: () => true});

                // Randomize a few properties to reduce fingerprinting consistency
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => Math.floor(Math.random() * 4) + 4});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => Math.floor(Math.random() * 8) + 4});

                // Override user agent to appear more like a real user
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
                });

                // Prevent detection of headless mode
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: 'denied' });
                    }
                    return originalQuery(parameters);
                };

                // Add a small delay to actions to simulate real user timing
                setTimeout(() => {
                    console.log('Page adjustments applied after slight delay');
                }, Math.floor(Math.random() * 3000));
            """
        })

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "document.addEventListener('DOMContentLoaded', function() { console.log('Page fully loaded'); });"
        })

        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": 51.7700,
            "longitude": 12.990,
            "accuracy": 100
        })

        if self.browserConfig.get("sizes"):
            deviceHeight = self.browserConfig["sizes"]["height"]
            deviceWidth = self.browserConfig["sizes"]["width"]
        else:
            if self.mobile:
                deviceHeight = random.randint(568, 1024)
                deviceWidth = random.randint(320, min(576, int(deviceHeight * 0.7)))
            else:
                deviceWidth = random.randint(1024, 2560)
                deviceHeight = random.randint(768, min(1440, int(deviceWidth * 0.8)))
            self.browserConfig["sizes"] = {
                "height": deviceHeight,
                "width": deviceWidth,
            }
            Utils.saveBrowserConfig(self.userDataDir, self.browserConfig)

        if self.mobile:
            screenHeight = deviceHeight + 146
            screenWidth = deviceWidth
        else:
            screenWidth = deviceWidth + 55
            screenHeight = deviceHeight + 151

        logging.info(f"Screen size: {screenWidth}x{screenHeight}")
        logging.info(f"Device size: {deviceWidth}x{deviceHeight}")

        if self.mobile:
            driver.execute_cdp_cmd("Emulation.setTouchEmulationEnabled", {"enabled": True})

        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": deviceWidth,
                "height": deviceHeight,
                "deviceScaleFactor": 0,
                "mobile": self.mobile,
                "screenWidth": screenWidth,
                "screenHeight": screenHeight,
                "positionX": 0,
                "positionY": 0,
                "viewport": {
                    "x": 0,
                    "y": 0,
                    "width": deviceWidth,
                    "height": deviceHeight,
                    "scale": 1,
                },
            },
        )

        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            "platform": self.userAgentMetadata["platform"],
            "userAgentMetadata": self.userAgentMetadata,
        })

        return driver

    def setupProfiles(self) -> Path:
        sessionsDir = Utils.getProjectRoot() / "sessions"
        sessionid = f"{self.username}"
        sessionsDir = sessionsDir / sessionid
        sessionsDir.mkdir(parents=True, exist_ok=True)
        return sessionsDir

    @staticmethod
    def getCCodeLang(lang: str, geo: str) -> tuple:
        if lang is None or geo is None:
            try:
                nfo = ipapi.location()
            except RateLimited:
                logging.warning("Returning default", exc_info=True)
                return "de", "DE"
            if isinstance(nfo, dict):
                if lang is None:
                    lang = nfo["languages"].split(",")[0].split("-")[0]
                if geo is None:
                    geo = nfo["country"]
        return lang, geo

    @staticmethod
    def getChromeVersion() -> str:
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--start-minimized")
        driver = WebDriver(options=chrome_options)
        version = driver.capabilities["browserVersion"]
        driver.close()
        driver.quit()
        return version

    def getRemainingSearches(self, desktopAndMobile: bool = False) -> RemainingSearches | int:
        dashboard = self.utils.getDashboardData()
        searchPoints = 1
        counters = dashboard["userStatus"]["counters"]

        progressDesktop = counters["pcSearch"][0]["pointProgress"]
        targetDesktop = counters["pcSearch"][0]["pointProgressMax"]
        if len(counters["pcSearch"]) >= 2:
            progressDesktop += counters["pcSearch"][1]["pointProgress"]
            targetDesktop += counters["pcSearch"][1]["pointProgressMax"]
        if targetDesktop in [30, 90, 102]:
            searchPoints = 3
        elif targetDesktop == 50 or targetDesktop >= 170 or targetDesktop == 150:
            searchPoints = 5
        remainingDesktop = int((targetDesktop - progressDesktop) / searchPoints)
        remainingMobile = 0
        if dashboard["userStatus"]["levelInfo"]["activeLevel"] != "Level1":
            progressMobile = counters["mobileSearch"][0]["pointProgress"]
            targetMobile = counters["mobileSearch"][0]["pointProgressMax"]
            remainingMobile = int((targetMobile - progressMobile) / searchPoints)
        if desktopAndMobile:
            return remainingMobile
        return remainingDesktop
