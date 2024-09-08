import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import streamlit as st
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

# Function to log messages to a text file
def log_to_file(message, log_file='error_log.txt'):
    """Log a message to a specified text file."""
    with open(log_file, 'a') as file:
        file.write(f"{datetime.now()} - {message}\n")

# Helper function to convert Streamlit date to the required format
def convert_streamlit_date_to_str(date_obj):
    return date_obj.strftime('%d/%m/%Y')

def construire_url_tmp(date):
    """Construct the URL for the specified date to download the CSV data."""
    if isinstance(date, str):
        date = pd.to_datetime(date, format='%d/%m/%Y')
    
    date_formatee = date.strftime('%d/%m/%Y').replace('/', '%2F')
    base_url = 'https://www.bkam.ma/Marches/Principaux-indicateurs/Marche-obligataire/Marche-des-bons-de-tresor/Marche-secondaire/Taux-de-reference-des-bons-du-tresor'
    params = f'?date={date_formatee}&block=e1d6b9bbf87f86f8ba53e8518e882982#address-c3367fcefc5f524397748201aee5dab8-e1d6b9bbf87f86f8ba53e8518e882982'
    
    return f'{base_url}{params}'

def telecharger_csv_tmp(date, save_directory="downloads"):
    """Download the CSV data for the specified date and save it locally."""
    try:
        if isinstance(date, str):
            date = pd.to_datetime(date, format='%d/%m/%Y')
        
        url_page = construire_url_tmp(date)
        log_to_file(f"Fetching data from URL: {url_page}")

        # Use headers to mimic a real browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.bkam.ma"
        }

        response = requests.get(url_page, headers=headers)
        log_to_file(f"HTTP response status code: {response.status_code}")

        # Raise HTTP error if the status is not successful
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        
        if table is not None:
            headers = [header.text.strip() for header in table.find_all('th')]
            rows = []
            for row in table.find_all('tr')[1:]:
                row_data = [value.text.strip() for value in row.find_all('td')]
                if "Total" not in row_data:
                    rows.append(row_data)
            
            df = pd.DataFrame(rows, columns=headers)
            
            # Rename and clean columns
            df['Date déchéance'] = df['Date d\'échéance']
            df = df.drop(['Transaction', 'Date d\'échéance'], axis=1)
            
            # Create the directory if it does not exist
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)

            # Define file name and save path
            filename = f"BKAM_Data_{date.strftime('%Y-%m-%d')}.csv"
            save_path = os.path.join(save_directory, filename)
            
            # Save the DataFrame to a CSV file
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            log_to_file(f"Data saved successfully to {save_path}")
            return df  # Return the DataFrame

        else:
            log_to_file(f"No table found in the HTML response for the URL: {url_page}")
            return pd.DataFrame()

    except requests.HTTPError as http_err:
        log_to_file(f"HTTP error occurred: {http_err}")
        return pd.DataFrame()
    except requests.RequestException as req_err:
        log_to_file(f"Request error occurred: {req_err}")
        return pd.DataFrame()
    except Exception as e:
        log_to_file(f"An error occurred: {e}")
        return pd.DataFrame()
import playwright.sync_api as playwright_sync
from playwright.sync_api import sync_playwright

def get_data_with_playwright(url):
    """Fetch page using Playwright to bypass 403 issues."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)

            # Wait for the page to fully load
            page.wait_for_load_state("networkidle")

            # Extract the page content
            page_source = page.content()

            # Close the browser
            browser.close()

            return page_source
    except Exception as e:
        log_to_file(f"Playwright error: {e}")
        return None
def main():
    st.title("Test Data Fetching and Logging with 403 Handling (Playwright)")
    
    # Input date picker
    selected_date = st.date_input("Select Date", datetime.today())
    
    # Fetch data for the selected date using requests or Playwright
    df = telecharger_csv_tmp(selected_date)
    
    if df.empty:
        st.error("Failed to retrieve data. Trying with Playwright...")
        url = construire_url_tmp(selected_date)
        page_source = get_data_with_playwright(url)
        if page_source:
            st.success("Data fetched using Playwright!")
            st.write(page_source)  # Display raw HTML content for now
        else:
            st.error("Failed to retrieve data with Playwright. Check the log file.")
            with open('error_log.txt', 'r') as file:
                st.text(file.read())
    else:
        st.success("Data fetched successfully!")
        st.dataframe(df)
if __name__ == "__main__":
    main()
