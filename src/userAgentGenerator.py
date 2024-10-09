import random
from typing import Any

import requests
from requests import HTTPError, Response

from src.utils import Utils

#If you know why, you know why.
class GenerateUserAgent:
    """A class for generating user agents for Microsoft Rewards Farmer."""

    MOBILE_DEVICE = "K"

    USER_AGENT_TEMPLATES = {
        "chrome_pc": (
            "Mozilla/5.0"
            " ({system}) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/{app[chrome_reduced_version]} Safari/537.36"
        ),
        "chrome_mobile": (
            "Mozilla/5.0"
            " ({system}) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/{app[chrome_reduced_version]} Mobile Safari/537.36"
        ),
    }

    OS_PLATFORMS = {"win": "Windows NT 10.0", "android": "Linux"}
    OS_CPUS = {"win": "Win64; x64", "android": "Android 13"}

    def userAgent(
        self,
        browserConfig: dict[str, Any] | None,
        mobile: bool = False,
    ) -> tuple[str, dict[str, Any], Any]:
        """
        Generates a user agent string for either a mobile or PC device.

        Args:
            mobile: A boolean indicating whether the user agent should be generated for a mobile device.

        Returns:
            A string containing the user agent for the specified device.
        """

        system = self.getSystemComponents(mobile)
        app = self.getAppComponents(mobile)
        uaTemplate = (
            self.USER_AGENT_TEMPLATES.get("chrome_mobile", "")
            if mobile
            else self.USER_AGENT_TEMPLATES.get("chrome_pc", "")
        )

        newBrowserConfig = None
        if browserConfig is not None:
            platformVersion = browserConfig.get("userAgentMetadata")["platformVersion"]
        else:
            platformVersion = (
                f"{random.randint(9,13) if mobile else random.randint(1,15)}.0.0"
            )
            newBrowserConfig = {}
            newBrowserConfig["userAgentMetadata"] = {
                "platformVersion": platformVersion,
            }
        uaMetadata = {
            "mobile": mobile,
            "platform": "Android" if mobile else "Windows",
            "fullVersionList": [
                {"brand": "Not/A)Brand", "version": "99.0.0.0"},
                {"brand": "Chromium", "version": app["chrome_version"]},
            ],
            "brands": [
                {"brand": "Not/A)Brand", "version": "99"},
                {"brand": "Chromium", "version": app["chrome_major_version"]},
            ],
            "platformVersion": platformVersion,
            "architecture": "" if mobile else "x86",
            "bitness": "" if mobile else "64",
            "model": "",
        }

        return uaTemplate.format(system=system, app=app), uaMetadata, newBrowserConfig

    def getSystemComponents(self, mobile: bool) -> str:
        """
        Generates the system components for the user agent string.

        Args:
            mobile: A boolean indicating whether the user agent should be generated for a mobile device.

        Returns:
            A string containing the system components for the user agent string.
        """
        osId = self.OS_CPUS.get("android") if mobile else self.OS_CPUS.get("win")
        uaPlatform = (
            self.OS_PLATFORMS.get("android") if mobile else self.OS_PLATFORMS.get("win")
        )
        if mobile:
            osId = f"{osId}; {self.MOBILE_DEVICE}"
        return f"{uaPlatform}; {osId}"

    def getAppComponents(self, mobile: bool) -> dict[str, str]:
        """
        Generates the application components for the user agent string.

        Returns:
            A dictionary containing the application components for the user agent string.
        """
        chromeVersion = self.getChromeVersion()
        chromeMajorVersion = chromeVersion.split(".")[0]
        chromeReducedVersion = f"{chromeMajorVersion}.0.0.0"

        return {
            "chrome_version": chromeVersion,
            "chrome_major_version": chromeMajorVersion,
            "chrome_reduced_version": chromeReducedVersion,
        }

    def getChromeVersion(self) -> str:
        """
        Get the latest version of Google Chrome.

        Returns:
            str: The latest version of Google Chrome.
        """
        response = self.getWebdriverPage(
            "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
        )
        data = response.json()
        return data["channels"]["Stable"]["version"]

    @staticmethod
    def getWebdriverPage(url: str) -> Response:
        response = Utils.makeRequestsSession().get(url)
        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise HTTPError(
                f"Failed to get webdriver page {url}. "
                f"Status code: {response.status_code}"
            )
        return response
