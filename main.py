import argparse
import csv

from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from time import sleep
from tqdm import tqdm

if __name__ == "__main__":
    usage = "usage: %prog [options] arg"
    parser = argparse.ArgumentParser()

    parser.add_argument('--file', dest='file_name', default='myaccounts.csv',
                        help='Username and password in CSV format')
    parser.add_argument('--category', dest='category', default='special_offers', nargs='+',
                        help="Customize coupon categories. Use 'all' or a comma separated list")
    parser.add_argument('--parse-from', dest='parse_from', default=0,
                        help='Start parsing from designated account')
    parser.add_argument('--parse-to', dest='parse_to', default=999,
                        help='Stop parsing after designated account')

    args = parser.parse_args()

    with open(file=args.file_name, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        total_rows = len(rows)

        for i, row in enumerate(rows):
            if i < int(args.parse_from):
                print("Skipping the first {} accounts...".format(args.parse_from))
                continue

            if i > int(args.parse_to):
                print("Skipping the last {} accounts...".format(total_rows - args.parse_to))
                break

            browser = webdriver.Chrome()
            browser.set_window_size(1440, 900)
            browser.set_window_position(0, 800)
            login_url = "https://www.vons.com/account/sign-in.html"
            username = row['username']
            password = row['password']

            browser.get(login_url)

            print("Processing account({}/{}): {}...".format(i + 1, total_rows, username))
            # handle login
            while True:
                try:
                    uid = WebDriverWait(browser, 10).until(ec.presence_of_element_located(
                        (By.NAME, "userId")))
                    passwd = WebDriverWait(browser, 10).until(ec.presence_of_element_located(
                        (By.NAME, "inputPassword")))
                    uid.send_keys(username)
                    passwd.send_keys(password)
                    passwd.send_keys(Keys.ENTER)
                    break
                except TimeoutException:
                    print("Timeout loading login pager, retrying...")
                    browser.execute_script('window.stop();')
                    browser.refresh()

            # There are three kinds of pop-up screen
            # 1. Select Store
            # 2. Confirm Store
            # 3. T&C

            # handle Select Store pop-up window
            print("Handling Select Store pop-up window")
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
                    print("No Select Store pop-up window")
                    break
                except ElementNotVisibleException:
                    print("Make My Store button not visible, wait 1 seconds")
                    retry += 1
                    sleep(1)

            # handle Confirm Change Store pop-up window
            sleep(1)
            retry = 0
            while retry < 2:
                try:
                    ok_btn = WebDriverWait(browser, 5).until(
                        ec.presence_of_element_located((By.XPATH, '//button[contains(text(), "Ok")]')))
                    browser.execute_script("arguments[0].click();", ok_btn)
                    break
                except TimeoutException:
                    print("No Confirm Change Store window")
                    break
                except ElementNotVisibleException:
                    print("Confirm Change Store button not visible, wait 1 second")
                    retry += 1
                    sleep(1)

            # handle T&C pop-up window
            sleep(2)
            retry = 0
            while retry < 2:
                try:
                    close_btn = WebDriverWait(browser, 5).until(
                        ec.presence_of_element_located((By.XPATH, '//button//a[contains(text(), "Close")]')))
                    close_btn.click()
                    break
                except TimeoutException:
                    print("No T&C pop-up window")
                    break
                except ElementNotVisibleException:
                    print("Close button not visible, wait 1 second")
                    retry += 1
                    sleep(1)

            # handle T&C pop-up window the second time
            sleep(1)
            retry = 0
            while retry < 2:
                try:
                    close_btn = WebDriverWait(browser, 5).until(
                        ec.visibility_of_element_located((By.XPATH, '//button//a[contains(text(), "Close")]')))
                    close_btn.click()
                    break
                except TimeoutException or ElementNotInteractableException:
                    print("No T&C pop-up window")
                    break
                except ElementNotVisibleException:
                    print("Close button not visible, wait 1 seconds")
                    retry += 1
                    sleep(1)
            """
            # set store
            sleep(2)
            while retry < 2:
                try:
                    change_link = WebDriverWait(browser, 5).until(
                        ec.visibility_of_element_located((By.XPATH, '//*[@id="currentStoreAddressWWW"]')))
                    # //*[@id="header-top-left-section"]/span/a[3]
                    # /html/body/div[1]/div/div/div[1]/div/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/div/div[1]/span/a[3]
                    # //*[@id="currentStoreAddressWWW"]
                    change_link.click()
                except NoSuchElementException:
                    print("Error")
                    continue
            """
            # click J4U tab
            sleep(2)
            try:
                j4u_tab = WebDriverWait(browser, 5).until(
                    ec.presence_of_element_located((By.XPATH, '//a[@href="/justforu-guest.html"]')))
                j4u_tab.click()
            except NoSuchElementException:
                print("Cannot find J4U tab, skipping...")
                browser.close()
                continue

            # click coupon & deals tab
            # sleep(2)
            # try:
            #    coupon_and_deal_tab = WebDriverWait(browser, 10).until(
            #        EC.presence_of_element_located((By.XPATH, '//a[@href="/justforu/coupons-deals.html"]')))
            #    #//*[@id="leftNavStaticMenu"]/li[1]/a
            #    coupon_and_deal_tab.click()
            # except NoSuchElementException:
            #    print("Cannot find coupon and deals tab")

            # keep clicking load more button
            sleep(2)
            while True:
                try:
                    load_more_btn = WebDriverWait(browser, 2).until(
                        ec.presence_of_element_located((By.CLASS_NAME, "load-more")))
                    browser.execute_script("arguments[0].click();", load_more_btn)
                except TimeoutException:
                    print("Done loading all the coupons")
                    break

            # add coupons
            added = []
            unadded = []
            xpath_added = "//div[contains(@class, 'coupon-clip-button')]//span[text()='ADDED']"
            xpath_unadded = "//div[contains(@class, 'coupon-clip-button')]//button[text()='ADD']"

            try:
                unadded = WebDriverWait(browser, 3).until(
                    ec.presence_of_all_elements_located((By.XPATH, xpath_unadded)))
            except TimeoutException:
                print("Timeout. Cannot find any unadded coupons")
                browser.close()
                continue

            try:
                added = WebDriverWait(browser, 3).until(
                    ec.presence_of_all_elements_located((By.XPATH, xpath_added)))
            except TimeoutException:
                print("Timeout. Cannot find any added coupons")

            print('Added: {}; unadded: {}'.format(len(added), len(unadded)))

            sleep(0.1)
            if len(unadded) == 0:
                print('No coupon to be added')

            t_coupons = tqdm(unadded)
            for coupon in t_coupons:
                t_coupons.set_description(desc='Adding new coupons ... ', refresh=True)
                browser.execute_script("arguments[0].click();", coupon)
                sleep(0.01)

            browser.close()
