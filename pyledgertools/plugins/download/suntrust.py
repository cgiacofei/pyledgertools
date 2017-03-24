"""Parsing for suntrust."""

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from yapsy.IPlugin import IPlugin
import time


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

        login_url = 'https://onlinebanking.suntrust.com'
        user = config['webuser']
        pswd = config['webpswd']

        driver = webdriver.PhantomJS()
        #driver = webdriver.Firefox()

        driver.get(login_url)
        driver.find_element_by_id('userId').send_keys(user)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(pswd)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(Keys.RETURN)
        time.sleep(10)
        # Fancy scraping stuff goes here
        print(driver.page_source)
        driver.quit()

        # Process to csv here
