import argparse
import csv

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from time import sleep
from tqdm import tqdm

if __name__ == "__main__":
    usage = "usage: %prog [options] arg"
    parser = argparse.ArgumentParser()

    parser.add_argument('--file', dest='file_name', default='myaccounts.csv',
                        help="Username and password in CSV format")
    parser.add_argument('--category', dest='category', default='special_offers', nargs='+',
                        help="Customize coupon categories. Use 'all' or a comma separated list")
    parser.add_argument('--include', dest='inclusions', default='0-999',
                        help="Specify the accounts to be parsed in a-b,c,d-f format (inclusive)")
    parser.add_argument('--exclude', dest='exclusions', default='',
                        help="Specify the accounts not to be parsed in the inclusion list")
    parser.add_argument('--browser', dest='browser', default='firefox',
                        help="Select browser between firefox and chrome; driver support is required")
    parser.add_argument('--headless', dest='headless', default=True, type=bool,
                        help="Set True to run in headless mode")

    args = parser.parse_args()

    supported_browsers = ['firefox', 'chrome']
    if str(args.browser).lower() not in supported_browsers:
        print("Please use supported browsers: {}".format(", ".join(supported_browsers)))

    inclusions = set()
    intervals = str(args.inclusions).split(',')

    for interval in intervals:
        begin_end = interval.split('-')
        if len(begin_end) == 1:     # a
            inclusions.add([int(begin_end[0])])
        elif len(begin_end) == 2:   # a-b
            inclusions |= set(range(int(begin_end[0]), int(begin_end[1]) + 1))
        else:
            continue

    exclusions = set()
    intervals = str(args.exclusions).split(',')
    if len(intervals[0]) > 0:
        for interval in intervals:
            begin_end = interval.split('-')
            if len(begin_end) == 1:     # a
                exclusions.add([int(begin_end[0])])
            elif len(begin_end) == 2:   # a-b
                exclusions |= set(range(int(begin_end[0]), int(begin_end[1]) + 1))
            else:
                continue

        inclusions -= exclusions

    with open(file=args.file_name, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        total_rows = len(rows)

        for i, row in enumerate(rows):
            if i not in inclusions:
                continue

            try:
                # Firefox seems to be more stable than Chrome
                if str(args.browser).lower() == 'firefox':
                    ff_options = Options()
                    if args.headless:
                        ff_options.headless = True
                    browser = webdriver.Firefox(options=ff_options, executable_path='geckodriver.exe')
                elif str(args.browser).lower() == 'chrome':
                    ch_options = Options()
                    if args.headless:
                        ch_options.add_argument("--headless")
                    browser = webdriver.Chrome("chromedriver.exe", options=ch_options)
                # elif for additional browser support
            except SessionNotCreatedException as e:
                print(e.msg)
                browser.close()

            browser.set_window_size(1200, 800)
            # browser.set_window_position(0, 800)
            login_url = 'https://www.safeway.com/account/sign-in.html'
            username = row['username']
            password = row['password']

            browser.get(login_url)

            print("Processing account({}/{}): {}...".format(i + 1, total_rows, username))
            # handle login
            while True:
                try:
                    uid = WebDriverWait(browser, 10).until(ec.presence_of_element_located(
                        (By.NAME, 'userId')))
                    passwd = WebDriverWait(browser, 10).until(ec.presence_of_element_located(
                        (By.NAME, 'inputPassword')))
                    sleep(1)
                    uid.send_keys(username)
                    passwd.send_keys(password)
                    passwd.send_keys(Keys.ENTER)
                    break
                except StaleElementReferenceException:
                    print("Referred element was reloaded...")
                    browser.execute_script('window.stop();')
                    browser.refresh()
                except TimeoutException:
                    print("Timeout loading login pager, retrying...")
                    browser.execute_script('window.stop();')
                    browser.refresh()

            # There are three kinds of pop-up screen
            # 1. Select Store
            # 2. Confirm Store
            # 3. T&C

            # handle Select Store pop-up window
            print("Handling Select Store pop-up window.")
            retry = 0
            while retry < 2:
                try:
                    make_my_store_btn = WebDriverWait(browser, 10).until(
                        ec.visibility_of_element_located((By.XPATH, '//*[@id="fulfillment-conflict-modal__button"]')))
                    sleep(1)
                    make_my_store_btn.click()
                    # there seems to be a bug that the button has no response but we have to refresh the web page
                    sleep(0.5)
                    browser.refresh()
                    break
                except TimeoutException or ElementNotInteractableException:
                    print("No Select Store pop-up window.")
                    break
                except ElementNotVisibleException:
                    print("Make My Store button not visible, wait 1 seconds.")
                    retry += 1
                    sleep(1)

            # click J4U tab
            sleep(2)
            retry = 0
            while retry < 2:
                try:
                    j4u_tab = WebDriverWait(browser, 5).until(
                        ec.presence_of_element_located((By.XPATH, '//a[@href="/foru-guest.html"]')))
                    sleep(1)
                    j4u_tab.click()
                    break
                # except ElementClickInterceptedException:
                #    print("Store confirmation window is blocking. Try refreshing the page...")
                #    browser.refresh()
                #    retry += 1
                #    continue
                except TimeoutException:
                    print("Time out. Try refreshing the page...")
                    browser.refresh()
                    retry += 1
                    continue
                except NoSuchElementException:
                    print("Cannot find J4U tab, skipping...")
                    browser.close()
                    continue

            # keep clicking load more button
            sleep(2)
            print("Loading coupons...")
            while True:
                try:
                    load_more_btn = WebDriverWait(browser, 10).until(
                        ec.presence_of_element_located((By.CLASS_NAME, 'load-more')))
                    browser.execute_script('arguments[0].click();', load_more_btn)
                except TimeoutException:
                    print("Done loading all the coupons.")
                    break

            # scan free items
            free_items = []
            free_item_xpath = "//span[text()='FREE']"

            print("Looking for free items...")
            try:
                free_items = WebDriverWait(browser, 3).until(
                    ec.presence_of_all_elements_located((By.XPATH, free_item_xpath)))
            except TimeoutException:
                print("Timeout.")

            print("Found {} free item(s).".format(len(free_items)))

            # add coupons
            added = []
            unadded = []
            xpath_added = "//span[contains(@class, 'coupon-clipped-container')]"
            xpath_unadded = "//div[contains(@class, 'coupon-clip-button')]//button[text()='Clip Coupon']"

            try:
                added = WebDriverWait(browser, 3).until(
                    ec.presence_of_all_elements_located((By.XPATH, xpath_added)))
            except TimeoutException:
                print("Timeout. Cannot find any added coupons.")

            print("Added: {}".format(len(added)))

            try:
                unadded = WebDriverWait(browser, 3).until(
                    ec.presence_of_all_elements_located((By.XPATH, xpath_unadded)))
            except TimeoutException:
                print("Unadded: {}".format(len(unadded)))
                print("Timeout. Cannot find any unadded coupons.")
                browser.close()
                sleep(1)
                continue

            print("Unadded: {}".format(len(unadded)))

            sleep(0.1)
            if len(unadded) == 0:
                print("No coupon to be added.")

            t_coupons = tqdm(unadded)
            for coupon in t_coupons:
                t_coupons.set_description(desc="Adding new coupons ... ", refresh=True)
                browser.execute_script('arguments[0].click();', coupon)
                sleep(0.01)

            browser.close()