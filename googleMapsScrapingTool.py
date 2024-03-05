from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import requests
from requests.exceptions import RequestException, Timeout, HTTPError, ConnectionError
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

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
        time.sleep(10) # This is a time delay to allow time for the user to accept or deny Google's terms.
        self._selenium_extractor()

    def _selenium_extractor(self):
        action = ActionChains(self.browser)
        prev_length = 0
        print("\nScraping has started. We'll let you know when we're done. This could take a few minutes. Please do not close the browser window or minimize it (the script will stop if you do so).")

        while len(self._get_elements()) < 1000: # This is the number of results per page. Google seemingly has a hard limit of 120, but 1000 ensures that it runs smoothly.
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
            self.browser.execute_script("arguments[0].scrollIntoView();", element)
            element.click() # Clicks each element to prepare for extracting of information
            time.sleep(2)
            source = self.browser.page_source
            soup = BeautifulSoup(source, 'html.parser')
            try:
                # Retrieve the names
                name_html = soup.find('h1', {"class": "DUwDvf lfPIob"})
                name = name_html.text.strip()
                info_divs = soup.findAll('div', {"class": "Io6YTe fontBodyMedium kR99db"}) # Represent the element that holds the other information
                phone = "Not available"
                for j in range(len(info_divs)):
                    if re.match(r'^(\+[\d\s()-]*|\d+[\d\s()-]*)$', info_divs[j].text.strip()): # Check if the phone number is in the format of a phone number
                        phone = info_divs[j].text
                # Address is extracted from a field in the same div as the phone number
                address_html = info_divs[0].text
                address = address_html
                website_html = soup.find('a', {"class": "CsEnBe", "data-item-id": "authority"}) # Find element with 'href' attribute (more reliable and includes 'https://' part of addresses)
                if website_html:
                    website = website_html.get('href')
                else:
                    website = "Not available"
                    
                emails = "Not available" # Reset emails variable before attempting to extract from the current website
                # Check gathered websites for email addresses
                for j in range(len(info_divs)):
                    if website_html:
                        try:
                            website_source = requests.get(website, timeout=10).text
                            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', website_source) # Checks if the email address is in a correct format
                            emails = [email for email in emails if not email.endswith('.wixpress.com')] # Removes results with '.wixpress.com' domain
                            emails = list(set(emails)) #Stores email addresses (there can be multiple for each result)
                            if not emails:
                                emails = "Not available"
                        # Various issues could happen during attempted extraction of email addresses
                        except (Timeout, ConnectionError) as ex:
                            print("Error scraping emails from website due to network issues:", ex)
                        except HTTPError as ex:
                            print("HTTP error occurred while accessing the website:", ex)
                        except RequestException as ex:
                            print("An error occurred while accessing the website:", ex)
                    # If no website, there are certainly no email addresses
                    else:
                        website = "Not available"
                        emails = "Not available"
                print([name, phone, address, website, emails]) # Preview of information from each result to go into CSV
                self.csv_data.append([name, phone, address, website, emails]) # Appending for printing to CSV
            except Exception as ex:
                print("Error occurred:", ex)
                continue

        print(self.csv_data)
        self._save_to_csv()

    def _get_elements(self):
        return self.browser.find_elements(By.CLASS_NAME, "hfpxzc") # Represents each Google Maps result on the left sidebar

    def _save_to_csv(self):
        print("\nData scraped. Making CSV file...")
        df = pd.DataFrame(self.csv_data, columns=['Business Name', 'Phone', 'Street Address', 'Website', 'Email Addresses'])
        df.to_csv(filename + '.csv', index=False, encoding='utf-8')
        print("\nCSV file made successfully. Check the directory of this app's location for your resulting file. Remember to not give files names which are already in use within the same directory as the .exe (they will overwrite).\n\nNOTE: There may be some useless information in 'Email Addresses' column, as some other pieces of information may be scanned as email addresses in addition to the actual email addresses.\n")

if __name__ == "__main__":
    filename = input("\nPlease enter a file name (a name which is unique to the directory of this program) for the resulting CSV file: ")
    link = input("\nRemember to first make a selection on Google's cookies and data prompt in due time when Chrome opens (~10 seconds). Please enter the Google Maps link for scraping: ")
    scraper = GoogleMapsScraper(link)
    scraper.scrape()