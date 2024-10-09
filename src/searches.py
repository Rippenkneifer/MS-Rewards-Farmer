from enum import Enum, auto
from typing import Final
from src.browser import Browser
from src.utils import Utils

LOAD_DATE_KEY = "loadDate"

class RetriesStrategy(Enum):
    EXPONENTIAL = auto()
    CONSTANT = auto()
class Searches:
    config = Utils.loadConfig()
    maxRetries: Final[int] = config.get("retries", {}).get("max", 3)
    baseDelay: Final[float] = config.get("retries", {}).get("base_delay_in_seconds", 5)
    retriesStrategy = RetriesStrategy[config.get("retries", {}).get("strategy", RetriesStrategy.CONSTANT.name)]
    def __init__(self, browser: Browser):
        self.counter = 0
        #self.maxCounter = 0
        self.browser = browser
        self.webdriver = browser.webdriver






