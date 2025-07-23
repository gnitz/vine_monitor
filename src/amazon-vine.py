import sys
import re
import time
import logging
import copy
from typing import Set
from typing_extensions import Final
import urllib.request
import urllib.error
import urllib.parse
# import webbrowser # This is now only used inside a function, can be moved for clarity
import datetime
import subprocess
import http.cookiejar

import browsercookie
import bs4
import fake_useragent
import mechanize

import getpass
from optparse import OptionParser


INITIAL_PAGE: Final = 'https://www.amazon.co.uk/vine/vine-items?queue=potluck'
QUEUE_URL: Final = 'https://www.amazon.co.uk/vine/vine-items?queue=encore'
AFA_URL: Final = 'https://www.amazon.co.uk/vine/vine-items?queue=last_chance'
USER_AGENT: Final[str] = fake_useragent.UserAgent().ff

def setup_logging():
    """Configure logging to file and console."""
    # Using basicConfig for simplicity. For more complex needs, you could
    # create logger objects and add handlers manually.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("vine_monitor.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def create_browser() -> mechanize.Browser:
    browser = mechanize.Browser()
    firefox = getattr(browsercookie, OPTIONS.browser)()

    # Create a new cookie jar for Mechanize
    cj = http.cookiejar.CookieJar()
    for cookie in firefox:
        cj.set_cookie(copy.copy(cookie))
    browser.set_cookiejar(cj)

    # Necessary for Amazon.com
    browser.set_handle_robots(False)
    browser.addheaders = [('User-agent', USER_AGENT)]

    try:
        logging.info('Connecting to Amazon Vine...')
        html = browser.open(INITIAL_PAGE).read()

        # Are we already logged in?
        if b'Vine Help' in html:
            logging.info("Successfully logged in with a browser cookie.")
            return browser

        logging.critical('Could not log in with a cookie. Check browser session.')
        sys.exit(1)
    except urllib.error.HTTPError as e:
        logging.critical("HTTP Error during login: %s", e)
    except urllib.error.URLError as e:
        logging.critical('URL Error during login: %s', e)
    except Exception:
        logging.critical("An unexpected error occurred during login.", exc_info=True)

    sys.exit(1)


def download_vine_page(br, url, name=None):
    if name:
        logging.info("Checking %s...", name)
    try:
        logging.debug("Downloading page: %s", url)
        response = br.open(url)
        html = response.read()
        logging.debug("Parsing page...")
        return bs4.BeautifulSoup(html, features="lxml")
    except Exception as e:
        logging.error("Failed to download or parse page %s: %s", url, e)
        return None



def get_list(br, url, name) -> Set[str]:
    soup = download_vine_page(br, url, name)
    if not soup:
        logging.error("Could not get soup object for %s, returning empty list.", name)
        return set()

    asins: Set[str] = set()

    for link in soup.find_all('tr', {'class': 'v_newsletter_item'}):
        if link['id'] in asins:
            logging.warning('Duplicate in-stock item found in %s: %s', name, link['id'])
        asins.add(link['id'])

    # Find list of out-of-stock items.  All of items listed in the
    # 'vineInitalJson' variable are out of stock.  Also, Amazon's web
    # developers don't know how to spell.  "Inital"?  Seriously?
    for script in soup.find_all('script', {'type': 'text/javascript'}):
        for s in script.findAll(text=True):
            m = re.search(r'^.*vineInitalJson(.*?)$', s, re.MULTILINE)
            if m:
                # {asin:"B007XPLI56"},
                oos = re.findall(
                    '{"asin":"([^"]*)"}', m.group(0))

                # Remove all out-of-stock items from our list
                asins.difference_update(oos)

    logging.info('Found %u in-stock items in %s.', len(asins), name)
    return asins


def open_product_page(br, link, url) -> bool:
    import webbrowser
    logging.debug("Attempting to open product page for ASIN: %s", link)
    soup = download_vine_page(br, url % link)
    # Make sure we don't get a 404 or some other error
    if soup:
        logging.info('New item found: %s', link)
        # Display how much tax it costs
        tags = soup.find_all('p', text=re.compile(
            'Estimated tax value : \$[0-9\.]*'))
        if tags:
            tag = tags[0].contents[0]
            m = re.search('\$([0-9\.]*)', tag)
            if m:
                cost = float(m.group(1))
                logging.info('  Tax cost: $%.2f', cost)
        webbrowser.open_new_tab(url % link)
        time.sleep(1)
        return True
    else:
        logging.warning('Invalid item page or error for ASIN: %s', link)
        return False


parser = OptionParser(usage="usage: %prog [options]")
parser.add_option("-w", dest="wait",
                  help="Number of minutes to wait between iterations (default is %default minutes)",
                  type="int", default=10)
parser.add_option('--browser', dest='browser',
                  help='Which browser to use ("firefox" or "chrome") from which to load the session cookies (default is "%default")',
                  type="string", default='firefox')

(OPTIONS, _args) = parser.parse_args()

setup_logging()
logging.info("Vine Monitor starting up.")
logging.info("Using browser: %s", OPTIONS.browser)
logging.info("Check interval: %d minutes", OPTIONS.wait)

BROWSER: Final = create_browser()

your_queue_list = get_list(BROWSER, QUEUE_URL, "your queue")
vine_for_all_list = get_list(BROWSER, AFA_URL, "Available for all")

if not your_queue_list and not vine_for_all_list:
    logging.critical('Cannot get initial item lists. Exiting.')
    sys.exit(1)


while True:
    logging.info("Waiting %u minute%s for the next check.",
                 OPTIONS.wait, 's'[OPTIONS.wait == 1:])
    time.sleep(OPTIONS.wait * 60)

    your_queue_list2 = get_list(BROWSER, QUEUE_URL, "Your Queue")
    if your_queue_list2:
        for link in your_queue_list2.copy():
            if link not in your_queue_list:
                if not open_product_page(BROWSER, link, 'https://www.amazon.co.uk/vine/vine-items?queue=potluck'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    your_queue_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        your_queue_list = your_queue_list2

    vine_for_all_list2 = get_list(BROWSER, AFA_URL, "Available for all")
    if vine_for_all_list2:
        for link in vine_for_all_list2.copy():
            if link not in vine_for_all_list:
                if not open_product_page(BROWSER, link, 'https://www.amazon.co.uk/vine/vine-items?queue=last_chance'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    vine_for_all_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        vine_for_all_list = vine_for_all_list2
