"""Parsing for suntrust."""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import json
from yapsy.IPlugin import IPlugin
import time
import sys


def extract_from_row(row):
    strip_strings = [
        'ELECTRONIC/ACH DEBIT',
        'CHECK CARD PURCHASE',
    ]

    json_data = {}
    cells = row.find_all('td')

    if cells:
        data = [x.text for x in cells if x.text != '']
        raw_date = data[0]
        payee = data[1]
        for strip in strip_strings:
            payee = payee.replace(strip, '')

        p_regex = '([-]*)\s*(\$)(\d+.\d+)'
        d_regex = '.*(\d{2,2})/(\d{2,2})/(\d{4,4})'
        try:
            amount = data[2].replace(',', '')
            neg, cur, amt = re.match(p_regex, amount).groups()
            m, d, y = re.match(d_regex, raw_date).groups()
        except AttributeError:
            return json_data

        json_data = {
            'date': '{}-{}-{}'.format(y, m, d),
            'payee': ' '.join(payee.split()),
            'amount': '{}{}'.format(neg, amt.replace(',', '')),
            'currency': cur,
        }
    return json_data


def wait_for_element(driver, by, name):
    # Wait for table to load
    try:
        element_present = EC.presence_of_element_located((by, name))

        WebDriverWait(driver, 30).until(element_present)
    except TimeoutException:
        print('Timed out waiting for page to load', file=sys.stderr)
        return False

    return True


def login_suntrust(config):
    login_url = 'https://onlinebanking.suntrust.com'
    user = config['webuser']
    pswd = config['webpswd']

    driver = webdriver.PhantomJS()

    driver.get(login_url)

    driver.find_element_by_id('userId').send_keys(user)
    driver.find_element_by_xpath('//input[@type="password"]').send_keys(pswd)
    driver.find_element_by_xpath('//input[@type="password"]').send_keys(
        Keys.RETURN
    )

    wait_for_element(driver, By.CLASS_NAME, 'suntrust-transactions-header')
    time.sleep(5)
    return driver


def get_rows_from_soup(soup):
    table = soup.find('table', class_='suntrust-transactions')
    tbody = table.find('tbody')
    return tbody.find_all('tr')


def push_load_button(driver):
    b_container = driver.find_element_by_class_name(
        'suntrust-loader-container'
    )
    load_button = b_container.find_element_by_tag_name('button')
    load_button.click()


class SuntrustScraper(IPlugin):
    """Main plugin class forz the suntrust scraper."""

    def download(self, config):
        """Download method

        Arguments:
            config (dict): All the info needed for the scraper goes here.

        Returns:
            str:
                Path to csv file containing scraped info.
        """
        save_file = '/tmp/suntrust_scrape.json'
        start = config['dtstart']
        end = config['dtend']

        outfile = open(save_file, 'w')
        infile = config.get('input_file', None)

        # Load html file if given
        # No validation is happening here so import will fail spectacularly if
        # a non-HTML file is given.
        if infile:
            with open(infile, 'r') as html:
                page_source = html.read()
            print('HTML file loaded', file=sys.stderr)
        else:
            driver = login_suntrust(config)
            print('Logged in to Suntrust', file=sys.stderr)
            page_source = driver.page_source

        soup = BeautifulSoup(page_source, 'html.parser')
        rows = get_rows_from_soup(soup)

        json_output = []

        found_start = False
        while not found_start and not infile:
            last_row = rows[-1]
            data = extract_from_row(last_row)
            if data['date'].replace('-', '') >= start:
                print('Loading...', data['date'], file=sys.stderr)
                try:
                    push_load_button(driver)
                except:
                    found_start = True

                time.sleep(5)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                rows = get_rows_from_soup(soup)
            else:
                found_start = True

        for row in rows:
            json_data = extract_from_row(row)
            dstring = json_data.get('date', '').replace('-', '')
            if dstring >= start and dstring <= end:
                json_output.append(json_data)

        with open(save_file, 'w') as outfile:
            json.dump(json_output, outfile)

        driver.quit()

        return save_file
