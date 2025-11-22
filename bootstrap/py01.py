#!/usr/bin/env python3
"""
stealth_text_io.py  ·  part of the Advanced Stealth Web-Automation system
"""
import sys, time, random, logging, pathlib, textwrap
from typing import Optional, List

# --- third-party ---
import undetected_chromedriver as uc                   # :contentReference[oaicite:0]{index=0}
from selenium.webdriver.common.by import By            # :contentReference[oaicite:1]{index=1}
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup                          # :contentReference[oaicite:2]{index=2}
import pyautogui                                       # :contentReference[oaicite:3]{index=3}

# ---------- 0. config ----------
INPUT_FILE   = pathlib.Path("input-text-01.txt")
OUTPUT_FILE  = pathlib.Path("output-text-01.txt")
LOG_FILE     = pathlib.Path("test-debug.log")
WAIT_SECONDS = 20

# ---------- 1. logging ----------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("stealth-bot")

# ---------- 2. helpers ----------
def _human_pause(a: float = 0.10, b: float = 0.35) -> None:
    time.sleep(random.uniform(a, b))

def _visible(el) -> bool:
    try:
        return el.is_displayed()
    except Exception:
        return False

def find_input_candidates(driver) -> List:
    """
    Return a list of input/textarea WebElements roughly ordered by width
    """
    selectors = [
        "input[type='text']",
        "input[type='search']",
        "textarea",
        "input:not([type])"
    ]
    cand = []
    for sel in selectors:
        cand.extend(driver.find_elements(By.CSS_SELECTOR, sel))   # :contentReference[oaicite:4]{index=4}
    # keep only visible & large-ish ones
    cand = [c for c in cand if _visible(c)]
    cand.sort(key=lambda e: e.size.get("width", 0), reverse=True)
    return cand

def locate_main_input(driver):
    log.debug("Locating main text input …")
    for el in find_input_candidates(driver):
        placeholder = (el.get_attribute("placeholder") or "").lower()
        aria_label  = (el.get_attribute("aria-label")  or "").lower()
        if any(k in placeholder for k in ("search", "message", "text")) or \
           any(k in aria_label  for k in ("search", "query", "message")):
            log.debug("Heuristic matched via placeholder/aria-label → %s", el)
            return el
    # else fallback to first candidate
    return find_input_candidates(driver)[0] if find_input_candidates(driver) else None

def locate_submit(driver, input_el):
    log.debug("Locating submit button …")
    # strategy 1 – same form
    try:
        form = input_el.find_element(By.XPATH, "./ancestor::form")
        log.debug("Found ancestor form, scanning for <input type=submit> or <button> …")
        buttons = form.find_elements(By.CSS_SELECTOR,
                    "input[type='submit'], button[type='submit'], button")
        for b in buttons:
            if _visible(b):
                return b
    except NoSuchElementException:
        pass
    # strategy 2 – buttons with common text
    common = driver.find_elements(By.XPATH,
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'search') or "
        "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit') or "
        "contains(text(),'Go')]")
    return common[0] if common else None

def human_type(element, text: str):
    element.click()
    _human_pause()
    for ch in text:
        element.send_keys(ch)
        _human_pause(0.08, 0.25)                               # :contentReference[oaicite:5]{index=5}

def human_click(element):
    driver = element._parent
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    loc = element.location_once_scrolled_into_view
    size = element.size
    x = loc['x'] + size['width']/2 + random.randint(-3, 3)
    y = loc['y'] + size['height']/2 + random.randint(-3, 3)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.7))  # curved easing :contentReference[oaicite:6]{index=6}
    _human_pause()
    pyautogui.click()

def read_visible_text(driver) -> str:
    soup = BeautifulSoup(driver.page_source, "lxml")           # :contentReference[oaicite:7]{index=7}
    # crude but effective: strip script/style & return joined visible strings
    for t in soup(["script", "style", "noscript"]):
        t.extract()
    text = soup.get_text(" ", strip=True)
    return textwrap.shorten(text, 1000000)  # keep reasonable size

# ---------- 3. main workflow ----------
def main(url: str):
    # Read input text
    if not INPUT_FILE.exists():
        log.error("Input file %s not found!", INPUT_FILE); sys.exit(2)
    test_text = INPUT_FILE.read_text(encoding="utf-8").strip()
    log.info("Loaded %d characters from %s", len(test_text), INPUT_FILE)

    # Launch stealth browser
    log.info("Starting undetected-chromedriver session …")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options, headless=False, use_subprocess=True)  # :contentReference[oaicite:8]{index=8}

    try:
        log.info("Navigating to %s", url)
        driver.get(url)

        # Locate input widget
        inp = locate_main_input(driver)
        if not inp:
            log.error("Could not locate a suitable input element — aborting")
            return
        log.info("Typing test text …")
        human_type(inp, test_text)

        # Submit
        btn = locate_submit(driver, inp)
        if btn:
            log.info("Clicking submit button")
            human_click(btn)
        else:
            log.info("No submit button found → sending ENTER on input")
            inp.send_keys(Keys.ENTER)

        # Wait for response
        log.info("Waiting %s seconds for page to update …", WAIT_SECONDS)
        time.sleep(WAIT_SECONDS)                               # :contentReference[oaicite:9]{index=9}

        # Capture output
        log.info("Capturing result DOM …")
        out_text = read_visible_text(driver)
        OUTPUT_FILE.write_text(out_text, encoding="utf-8")
        log.info("Wrote %d characters to %s", len(out_text), OUTPUT_FILE)

    finally:
        driver.quit()
        log.info("Session closed.")

# ---------- 4. entry-point ----------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python stealth_text_io.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
