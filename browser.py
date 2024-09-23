import os
import platform

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


def get_chrome_driver():
    if platform.machine() == "aarch64":
        return "/usr/bin/chromedriver"
    if "chromedriver.exe" in os.listdir():
        return "./chromedriver.exe"
    return ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()


def fetch_page(url: str):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # https://github.com/SeleniumHQ/selenium/issues/14438#issuecomment-2311749195
    options.add_argument("headless=old")
    options.add_argument("--disable-search-engine-choice-screen")

    driver: webdriver.Chrome

    try:
        chrome_driver = get_chrome_driver()
        driver = webdriver.Chrome(
            service=Service(chrome_driver, port=9090), options=options
        )
    except Exception as e:
        print(f"Erro ao criar o driver do Chrome: {e}")
        return ""

    driver.get(url)
    WebDriverWait(driver, 5).until(
        lambda wd: driver.execute_script("return document.readyState") == "complete",
        "Page taking too long to load",
    )

    return driver.page_source


# print(fetch_page("https://inv.kamuridesu.com/feed/trending"))
