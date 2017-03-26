"""Parsing for suntrust."""

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import json
from yapsy.IPlugin import IPlugin


class SuntrustScraper(IPlugin):
    """Main plugin class for the suntrust scraper."""

    def download(self, config):
        """Download method

        Arguments:
            config (dict): All the info needed for the scraper goes here.

        Returns:
            str:
                Path to csv file containing scraped info.
        """
        save_file = '/tmp/suntrust_scrape.csv'
        login_url = 'https://onlinebanking.suntrust.com'
        user = config['webuser']
        pswd = config['webpswd']

        driver = webdriver.PhantomJS()

        driver.get(login_url)
        driver.find_element_by_id('userId').send_keys(user)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(pswd)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(Keys.RETURN)

        # Wait for table to load
        try:
            element_present = EC.presence_of_element_located((
                By.CLASS_NAME,
                'suntrust-transactions-header'
            ))

            WebDriverWait(driver, 30).until(element_present)
        except TimeoutException:
            print('Timed out waiting for page to load')

        # Find table header then move up one level to get entire table.
        # This is lame but there are no classes usable at the table level
        # to find it with.
        th = driver.find_element_by_class_name('suntrust-transactions-header')
        table = th.find_element_by_xpath('..')
        tbody = table.find_element_by_tag_name('tbody')

        outfile = open(save_file, 'w')

        json_output = []
        for row in tbody.find_elements_by_tag_name('tr'):
            cells = row.find_elements_by_tag_name('td')
            data = [x.get_attribute('textContent') for x in cells if x.get_attribute('textContent') != '']
            raw_date = data[0]
            payee = data[1]
            p_regex = '([-]*)\s*(\$)(\d+.\d+)'
            d_regex = '.*(\d{2,2})/(\d{2,2})/(\d{4,4})'
            neg, cur, amt = re.match(p_regex, data[2].strip(',')).groups()
            m, d, y = re.match(d_regex, raw_date).groups()

            json_data = {
                'date': '{}-{}-{}'.format(y, m, d),
                'payee': ' '.join(payee.split()),
                'amount': '{} {}{}'.format(cur, neg, amt),
            }

            json_output.append(json_data)

        with open(save_file, 'w') as outfile:
            json.dump(json_output, outfile)

        driver.quit()

        return save_file
