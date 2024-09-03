from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

import os
import humanfriendly
import argparse
import pandas as pd
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

def extract_data(driver):
    rows = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.fdat'))
    )

    data = []
    for row in rows:
        run_number = row.get_attribute('data-spgntr')
        num_files = row.find_element(By.CSS_SELECTOR, 'div.col-md-3.text-start').text
        num_bytes = row.find_element(By.CSS_SELECTOR, 'div.col-md-2.text-start').text
        num_bytes = humanfriendly.parse_size(num_bytes)
        data.append([int(run_number), int(num_files), num_bytes])
    return data

def save_to_csv(data, experiment_id):
    df = pd.DataFrame(data, columns=['Run Number', 'Number of Files', 'Total Size (bytes)'])
    filename = f'{experiment_id}.file_manager.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Crawl file manager.')
    parser.add_argument('exp', help='Experiment ID')
    parser.add_argument('--save-credentials', action='store_true', help='Save new credentials')
    args = parser.parse_args()

    store = CredentialStore()

    if args.save_credentials:
        store.save_credentials()
        print("Credentials saved. Please run the script again without --save-credentials to use them.")
        return

    try:
        credentials = store.load_credentials()
        username = credentials['username']
        password = credentials['password']
    except FileNotFoundError:
        print("Credentials not found. Please run the script with --save-credentials to set them up.")
        return

    driver = setup_driver()
    driver.get(f'https://pswww.slac.stanford.edu/lgbk/lgbk/{args.exp}/fileManager')

    try:
        login(driver, username, password)
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