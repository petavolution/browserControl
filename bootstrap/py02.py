#!/usr/bin/env python3
import logging
import time
import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

def setup_logger():
    """
    Configure a logger to output DEBUG messages both to console and to 'test-debug.log'.
    """
    logger = logging.getLogger('stealth_bot')
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)

    # File handler
    fh = logging.FileHandler('test-debug.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

def main():
    logger = setup_logger()

    TARGET_URL   = 'https://example.com'         # ← **Change this** to your target URL
    INPUT_FILE   = 'input-text-01.txt'           # ← must exist in working dir
    OUTPUT_FILE  = 'output-text-01.txt'          # ← will be created/overwritten

    logger.debug('🚀 Launching stealth Chrome WebDriver')
    driver = uc.Chrome()
    try:
        logger.debug(f'➡️ Navigating to {TARGET_URL}')
        driver.get(TARGET_URL)

        # — Locate the main text input field —
        logger.debug('🔍 Locating text input field')
        try:
            input_elem = driver.find_element('css selector', 'textarea')
        except NoSuchElementException:
            input_elem = driver.find_element('css selector', 'input[type="text"]')
        logger.debug(f'✅ Found input element: <{input_elem.tag_name}>')

        # — Read text from file and input it —
        logger.debug(f'📂 Reading input text from {INPUT_FILE}')
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.debug(f'✏️ Input text length: {len(text)} characters')
        input_elem.clear()
        input_elem.send_keys(text)
        logger.debug('✅ Text entered into field')

        # — Locate and click the submit button —
        logger.debug('🔍 Locating submit button')
        try:
            submit_btn = driver.find_element('css selector', 'button[type="submit"]')
        except NoSuchElementException:
            submit_btn = driver.find_element('css selector', 'input[type="submit"]')
        logger.debug(f'✋ Clicking on <{submit_btn.tag_name}> to submit')
        submit_btn.click()

        # — Wait for the response to load —
        logger.debug('⏱ Waiting 20 seconds for response')
        time.sleep(20)

        # — Parse the new DOM and extract response text —
        logger.debug('🔄 Parsing response from DOM')
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        # Extract all paragraphs; fallback to full text if none
        paragraphs = soup.find_all('p')
        if paragraphs:
            response = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            response = soup.get_text(separator="\n", strip=True)

        logger.debug(f'✍️ Writing response ({len(response)} characters) to {OUTPUT_FILE}')
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(response)
        logger.debug('✅ Output file written successfully')

    except Exception:
        logger.exception('❌ An unexpected error occurred')
    finally:
        driver.quit()
        logger.debug('🛑 WebDriver session closed')

if __name__ == '__main__':
    main()
