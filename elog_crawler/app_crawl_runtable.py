from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

import json
import argparse
import time
from .credential_store import CredentialStore

def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def login_if_necessary(driver, username, password):
    try:
        login_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Log in with S3DF (unix)')]"))
        )
        login_button.click()

        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login"))
        )
        username_field.send_keys(username)
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)

        submit_button = driver.find_element(By.ID, "submit-login")
        submit_button.click()
        print("Logged in successfully.")
    except TimeoutException:
        print("Login page not detected. User might already be logged in.")
    except NoSuchElementException:
        print("Login elements not found. Page structure might have changed or user is already logged in.")

def is_404_page(driver):
    try:
        status_code = driver.execute_script("return window.performance.getEntries()[0].responseStatus")
        if status_code == 404:
            return True
    except Exception:
        pass
    return False

def get_available_tabs(driver):
    tabs = []
    try:
        tab_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.nav-pills > li > a'))
        )
        tabs = [tab.text for tab in tab_elements]
    except Exception as e:
        print(f"Error getting available tabs: {str(e)}")
    return tabs

def scroll_to_bottom(driver, element):
    SCROLL_PAUSE_TIME = 0.5
    last_height = driver.execute_script("return arguments[0].scrollHeight", element)

    while True:
        # Scroll down to bottom
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return arguments[0].scrollHeight", element)
        if new_height == last_height:
            break
        last_height = new_height

def extract_data_production(driver):
    try:
        # Switch to the Data Production tab
        tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Data Production')]"))
        )
        tab.click()

        # Wait for the table container to load
        table_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "rtbl_content"))
        )

        # Scroll to ensure all content is loaded
        scroll_to_bottom(driver, table_container)

        # Find the table within the scrolled content
        table = table_container.find_element(By.CSS_SELECTOR, "table.table-striped")

        # Extract table headers with their data-col-idx attributes
        headers_with_idx = []
        header_rows = table.find_elements(By.TAG_NAME, "tr")[:2]  # Get the first two rows as headers
        for row in header_rows:
            for th in row.find_elements(By.TAG_NAME, "th"):
                header_text = th.text.strip()
                if header_text:
                    col_idx = th.get_attribute("data-col-idx")
                    if col_idx is not None:
                        headers_with_idx.append((header_text, int(col_idx)))

        # Sort headers by their data-col-idx
        headers_with_idx.sort(key=lambda x: x[1])
        headers = [h[0] for h in headers_with_idx]

        # Extract table rows
        rows = []
        for row in table.find_elements(By.TAG_NAME, "tr")[2:]:  # Skip header rows
            run_num = row.get_attribute("data-runnum")
            if run_num:
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = {"Run": run_num}

                # Match cells with headers based on data-col-idx
                for i, (header, idx) in enumerate(headers_with_idx):
                    if i < len(cells):
                        row_data[header] = cells[idx].text.strip()

                rows.append(row_data)

        return rows
    except Exception as e:
        print(f"Error extracting data from Data Production tab: {str(e)}")
        driver.save_screenshot('data_production_error.png')
        return None

def extract_detectors(driver):
    try:
        # Switch to the Detectors tab
        tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Detectors')]"))
        )
        tab.click()

        # Wait for the table container to load
        table_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "rtbl_content"))
        )

        # Scroll to ensure all content is loaded
        scroll_to_bottom(driver, table_container)

        # Find the table within the scrolled content
        table = table_container.find_element(By.CSS_SELECTOR, "table.table-striped")

        # Extract table headers
        headers = [header.text for header in table.find_elements(By.TAG_NAME, "th")]

        # Extract table rows
        rows = []
        for row in table.find_elements(By.TAG_NAME, "tr")[1:]:  # Skip header row
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = {}
            for i, cell in enumerate(cells):
                if i == 0:  # Assuming first column is the run number
                    row_data[headers[i]] = cell.text
                else:
                    # Check for checkbox status
                    checkbox = cell.find_elements(By.CSS_SELECTOR, "svg.fa-check")
                    row_data[headers[i]] = "Checked" if checkbox and checkbox[0].is_displayed() else "Unchecked"
            rows.append(row_data)

        return rows
    except Exception as e:
        print(f"Error extracting data from Detectors tab: {str(e)}")
        return None

def process_experiment(driver, experiment_id, username, password):
    print(f"Processing experiment: {experiment_id}")
    driver.get(f'https://pswww.slac.stanford.edu/lgbk/lgbk/{experiment_id}/runTables')

    login_if_necessary(driver, username, password)

    if is_404_page(driver):
        print(f"Experiment {experiment_id} not found (404 error). Skipping...")
        return

    experiment_data = {}
    try:
        available_tabs = get_available_tabs(driver)
        print(f"Available tabs for experiment {experiment_id}: {available_tabs}")

        if "Data Production" in available_tabs:
            data_production = extract_data_production(driver)
            if data_production:
                experiment_data["Data Production"] = data_production
            else:
                print("Failed to extract data from Data Production tab.")

        if "Detectors" in available_tabs:
            detectors = extract_detectors(driver)
            if detectors:
                experiment_data["Detectors"] = detectors
            else:
                print("Failed to extract data from Detectors tab.")

        if not experiment_data:
            print(f"No data could be extracted for experiment {experiment_id}.")

    except TimeoutException:
        print(f"Timed out waiting for the content to load for experiment {experiment_id}.")
        driver.save_screenshot(f'timeout_screenshot_{experiment_id}.png')
        experiment_data["error"] = "Timeout occurred while loading content"
    except WebDriverException as e:
        print(f"WebDriver error occurred while processing experiment {experiment_id}: {str(e)}")
        experiment_data["error"] = f"WebDriver error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error occurred while processing experiment {experiment_id}: {str(e)}")
        experiment_data["error"] = f"Unexpected error: {str(e)}"

    save_to_json(experiment_data, experiment_id)

def save_to_json(data, experiment_id):
    filename = f'{experiment_id}.runtable.json'
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Crawl experiment runtable page.')
    parser.add_argument('experiments', nargs='+', help='Experiment IDs (space-separated)')
    parser.add_argument('--reset-credentials', action='store_true', help='Reset saved credentials')
    parser.add_argument('--gui', action='store_true', help='Run with GUI (non-headless mode)')
    args = parser.parse_args()

    store = CredentialStore()

    if args.reset_credentials:
        store.delete_credentials()
        return

    username, password = store.get_credentials()

    driver = setup_driver(headless=not args.gui)

    try:
        for experiment_id in args.experiments:
            process_experiment(driver, experiment_id, username, password)
    except TimeoutException:
        print("Timed out waiting for the content to load.")
        driver.save_screenshot('timeout_screenshot.png')
    finally:
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()
