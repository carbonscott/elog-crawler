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
        # Wait for the iframe to be available
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.sitespecific_iframe"))
        )

        # Switch to the iframe
        driver.switch_to.frame(iframe)

        # Find the tabs within the iframe
        tab_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.nav-tabs > li > a'))
        )
        tabs = [tab.get_attribute('href').split('#')[-1] for tab in tab_elements]

    except WebDriverException as e:
        print(f"WebDriver error while getting available tabs: {str(e)}")
    except Exception as e:
        print(f"Error getting available tabs: {str(e)}")
    finally:
        # Ensure we switch back to default content even if an error occurred
        try:
            driver.switch_to.default_content()
        except:
            pass
    return tabs

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

def extract_tab_content(driver, tab_id):
    try:
        # Switch to the iframe
        iframe = driver.find_element(By.CSS_SELECTOR, "iframe.sitespecific_iframe")
        driver.switch_to.frame(iframe)

        # Click on the tab to activate it
        tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'a[href="#{tab_id}"]'))
        )
        tab.click()

        # Scroll to the bottom of the tab content
        scroll_to_bottom(driver)

        # Wait for the content to load
        content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, tab_id))
        )

        # Extract all text content from the tab
        tab_content = content.text

        # Switch back to the default content
        driver.switch_to.default_content()

        return tab_content
    except Exception as e:
        print(f"Error extracting content from tab {tab_id}: {str(e)}")
        driver.switch_to.default_content()
        return None

def extract_main_content(driver):
    try:
        # Look for the experiment details directly - first try specific div if it exists
        try:
            exp_details = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".exp_details, div[id*='details'], table.experiment-info"))
            )
            return exp_details.text
        except (TimeoutException, NoSuchElementException):
            # If specific selector fails, try finding by key labels that are visible in the screenshot
            # Look for elements containing labels like "Instrument:", "Start Time:", etc.
            key_labels = ["Instrument:", "Start Time:", "End Time:", "PI:", "Leader Account:"]
            content_parts = []

            for label in key_labels:
                try:
                    # Find elements containing each label
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{label}')]")
                    if elements:
                        # For each found element, get its parent or container to capture both label and value
                        for element in elements:
                            parent = element.find_element(By.XPATH, "./ancestor::tr") if "tr" in element.tag_name else element.find_element(By.XPATH, "./parent::*")
                            content_parts.append(parent.text)
                except:
                    continue

            if content_parts:
                return "\n".join(content_parts)

            # Last resort - fall back to original method
            body = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return body.text

    except Exception as e:
        print(f"Error extracting main content: {str(e)}")
        return "Unable to extract main content"

def process_experiment(driver, experiment_id, username, password):
    print(f"Processing experiment: {experiment_id}")
    driver.get(f'https://pswww.slac.stanford.edu/lgbk/lgbk/{experiment_id}/info')

    login_if_necessary(driver, username, password)

    if is_404_page(driver):
        print(f"Experiment {experiment_id} not found (404 error). Skipping...")
        return

    experiment_data = {}
    try:
        # Always extract main content
        experiment_data["main_content"] = extract_main_content(driver)

        available_tabs = get_available_tabs(driver)
        print(f"Available tabs for experiment {experiment_id}: {available_tabs}")

        if available_tabs:
            experiment_data["tabs"] = {}
            for tab in available_tabs:
                content = extract_tab_content(driver, tab)
                if content:
                    experiment_data["tabs"][tab] = content

        if not experiment_data["tabs"]:
            print(f"No tab content could be extracted for experiment {experiment_id}.")

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
    filename = f'{experiment_id}.info.json'
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Crawl experiment info page.')
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
