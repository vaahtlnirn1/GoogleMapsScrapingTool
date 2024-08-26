from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import requests
from requests.exceptions import RequestException, Timeout, HTTPError, ConnectionError
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GoogleMapsScraper:
    def __init__(self, link):
        self.link = link
        self.csv_data = []
        self.uniqueNames = []
        self.elementResults = 0
        self.browser = webdriver.Chrome()
        self.browser.maximize_window()

    def scrape(self):
        self.browser.get(str(self.link))
        try:
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".VfPpkd-LgbsSe.VfPpkd-LgbsSe-OWXEXe-k8QpJ.VfPpkd-LgbsSe-OWXEXe-dgl2Hf.nCP5yc.AjY5Oe.DuMIQc.LQeN7.XWZjwc")))
            accept_button = self.browser.find_element(By.CSS_SELECTOR, ".VfPpkd-LgbsSe.VfPpkd-LgbsSe-OWXEXe-k8QpJ.VfPpkd-LgbsSe-OWXEXe-dgl2Hf.nCP5yc.AjY5Oe.DuMIQc.LQeN7.XWZjwc")
            accept_button.click()  # Click the accept button for Google cookies and terms
        except Exception as e:
            print("Error accepting cookies:", e)
        self._selenium_extractor()

    def _selenium_extractor(self):
        prev_length = 0
        print("\nScraping has started. We'll let you know when we're done. This could take a few minutes. Please do not close the browser window or click the top and move it (the script will stop if you do so). Minimizing will not stop the script, but it will interfere with extraction of information (it will start duplicating the last entry).")
        while len(self._get_elements()) < 1000: # This limits the number of results per page. Google seemingly has a hard limit of 120, but 1000 ensures that it runs smoothly.
            # Acquiring elements to scrape
            print(len(self._get_elements()))
            var = len(self._get_elements())
            last_element = self._get_elements()[-1]
            self.browser.execute_script("arguments[0].scrollIntoView();", last_element)
            time.sleep(2) # Sleep allows time for page to load
            a = self._get_elements() 

            try:
                if len(a) == var:
                    self.elementResults += 1
                    if self.elementResults > 20 or len(a) == prev_length:
                        break
                else:
                    self.elementResults = 0
                prev_length = len(a)
            except StaleElementReferenceException:
                continue

        for element in self._get_elements():
            try:
                # Scroll element into view
                self.browser.execute_script("arguments[0].scrollIntoView();", element)
                element.click()
            except ElementClickInterceptedException:
                # Attempt to click the element using JavaScript as a fallback
                try:
                    self.browser.execute_script("arguments[0].click();", element)
                except Exception as e:
                    print(f"JavaScript click failed: {e}")
                    continue  # Skip to the next element if both attempts fail
            time.sleep(2)
            source = self.browser.page_source
            soup = BeautifulSoup(source, 'html.parser')
            try:
                # Retrieve the names
                name_html = soup.find('h1', {"class": "DUwDvf lfPIob"})
                name = name_html.text.strip()
                info_divs = soup.findAll('div', {"class": "m6QErb XiKgde"}) # Represents the element that holds all other information
                for j in range(len(info_divs)):
                    phone_field_html = soup.find(attrs={"data-item-id": lambda x: x and x.startswith("phone:tel:")})
                    if phone_field_html:
                        phone_html = phone_field_html.find('div', {"class": "Io6YTe fontBodyMedium kR99db fdkmkc"})
                        phone = phone_html.text.strip()
                    else:
                        phone = ""
                # Necessary due to Google's page layout with the address
                address_field_html = soup.find('button', {"class": "CsEnBe", "data-item-id": "address"})
                # Checks to ensure that it's not a rare case that a Google Maps result doesn't have an address (weird, I know..)
                if address_field_html:
                    address_html = address_field_html.find('div', {"class": "Io6YTe fontBodyMedium kR99db fdkmkc"})
                    address = address_html.text.strip()
                else:
                    address = ""
                website_html = soup.find('a', {"class": "CsEnBe", "data-item-id": "authority"}) # Find element with 'href' attribute
                if website_html:
                    website = website_html.get('href')
                else:
                    website = ""

                email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
                email_excluded_substrings = ['2x.png', 'sentry.io', '.wixpress.com']
                # Checks for 'phone' or 'website'. If neither, exclude the result.    
                if phone or website:    
                    emails = "" # Reset emails variable before attempting to extract from the current website
                    # Check gathered websites for email addresses
                    for j in range(len(info_divs)):
                        if website_html:
                            try:
                                website_source = requests.get(website, timeout=10).text
                                emails = re.findall(email_pattern, website_source) # Checks if the email address is in a correct format
                                emails = [email for email in emails if not any(substring in email for substring in email_excluded_substrings)] # Removes invalid results from emails
                                emails = list(set(emails)) #Stores email addresses (there can be multiple for each result)
                                if not emails:
                                    emails = ""
                            # Various issues could happen during attempted extraction of email addresses
                            except (Timeout, ConnectionError) as ex:
                                print("Error scraping emails from website due to network issues:", ex)
                            except HTTPError as ex:
                                print("HTTP error occurred while accessing the website:", ex)
                            except RequestException as ex:
                                print("An error occurred while accessing the website:", ex)
                        # If no website, there are certainly no email addresses
                        else:
                            website = ""
                            emails = ""
                    print([name, phone, website, emails, address]) # Preview of information from each result to go into CSV
                    self.csv_data.append([name, phone, website, emails, address]) # Appending for printing to CSV
            except Exception as ex:
                print("Error occurred:", ex)
                continue

        print(self.csv_data)
        self._save_to_csv()

    def _get_elements(self):
        return self.browser.find_elements(By.CLASS_NAME, "hfpxzc") # Represents each Google Maps result on the left sidebar

    def _save_to_csv(self):
        try:
            print("\nData scraped. Making CSV file...")
            df = pd.DataFrame(self.csv_data, columns=['Business Name', 'Phone', 'Website', 'Email Addresses', 'Street Address'])
            print(f"Saving to filename: {filename}.csv")
            df.to_csv(filename + '.csv', index=False, encoding='utf-8')
            print("\nCSV file made successfully. Check the directory of this app's location for your resulting file.")
        except Exception as e:
            print(f"Failed to save CSV file. Error: {e}")

if __name__ == "__main__":
    filename = input("\nPlease enter a file name (a name which is unique to the directory of this program) for the resulting CSV file: ")
    link = input("\nRemember to first make a selection on Google's cookies and data prompt in due time when Chrome opens (~10 seconds). Please enter the Google Maps link for scraping: ")
    scraper = GoogleMapsScraper(link)
    scraper.scrape()