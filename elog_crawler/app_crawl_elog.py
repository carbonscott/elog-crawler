from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import argparse
import time
from .credential_store import CredentialStore

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def login(driver, username, password):
    s3df_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Log in with S3DF (unix)')]"))
    )
    s3df_button.click()

    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login"))
    )
    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)

    submit_button = driver.find_element(By.ID, "submit-login")
    submit_button.click()

def scroll_to_bottom(driver):
    SCROLL_PAUSE_TIME = 1  # Increased pause time to allow content to load
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # If heights are the same, it's likely the end of the page
            # Try scrolling one more time to be sure
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # If still the same, we've reached the bottom
                break
        last_height = new_height

def get_element_text(parent_element, css_selector):
    try:
        return parent_element.find_element(By.CSS_SELECTOR, css_selector).text
    except NoSuchElementException:
        return ''

def extract_data(driver):
    entries = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.edat'))
    )

    data = []
    for entry in entries:
        posted = get_element_text(entry, 'div.col-2')
        run = get_element_text(entry, 'div.col-1')
        content = get_element_text(entry, 'div.col-5.elog_main_cnt')
        tags = get_element_text(entry, 'div.col-3.elog_main_cnt')
        author = get_element_text(entry, 'div.col-1.text-start')

        data.append([posted, run, content, tags, author])

    return data

def save_to_csv(data, experiment_id):
    df = pd.DataFrame(data, columns=['Posted', 'Run', 'Content', 'Tags', 'Author'])
    filename = f'{experiment_id}_logbook.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Crawl experiment logbook.')
    parser.add_argument('exp', help='Experiment ID')
    parser.add_argument('--reset-credentials', action='store_true', help='Reset saved credentials')
    args = parser.parse_args()

    store = CredentialStore()

    if args.reset_credentials:
        store.delete_credentials()
        return

    username, password = store.get_credentials()

    driver = setup_driver()
    driver.get(f'https://pswww.slac.stanford.edu/lgbk/lgbk/{args.exp}/eLog')

    try:
        login(driver, username, password)

        scroll_to_bottom(driver)
        data = extract_data(driver)

        for entry in data:
            print(entry)

        save_to_csv(data, args.exp)

    except TimeoutException:
        print("Timed out waiting for the content to load.")
        driver.save_screenshot('timeout_screenshot.png')

    finally:
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()
