import pandas as pd
import numpy as np
import re
import json

from fake_useragent import UserAgent
from selenium import webdriver
from bs4 import BeautifulSoup

exc_path = "C:/msys64/usr/bin/chromedriver.exe"

def tiki_search(search):
    ua = UserAgent()
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument(f'user-agent={ua.random}')
    driver = webdriver.Chrome(executable_path=exc_path, options=options)

    products = []
    for page_index in range(10):

        url = f"https://tiki.vn/search?q={search.replace(' ', '%20')}&page={page_index + 1}"
        driver.get(url)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")

        data_json = json.loads(soup.find(attrs={"id":"__NEXT_DATA__"}).text)
        products.extend(data_json['props']['initialState']['catalog']['data'])

    driver.close()

    tiki_prod = pd.DataFrame(products)

    del url, ua, options, driver, soup, data_json, products

    return tiki_prod

def laz_search(search):
    ua = UserAgent()
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument(f'user-agent={ua.random}')
    driver = webdriver.Chrome(executable_path=exc_path, options=options)

    products = []
    for page_index in range(10):

        url = f"https://www.lazada.vn/catalog/?page={page_index + 1}&q={search.replace(' ', '%20')}"
        driver.get(url)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        prod_items = soup.find_all('div', {'data-qa-locator': 'product-item'})

        for item in prod_items:
            prod_info = item.contents[0].contents[0].contents[1]

            item_info = {}

            item_info['page'] = page_index + 1
            item_info['index'] = item['data-listno']
            item_info['id'] = item['data-item-id']
            
            name = prod_info.find_all('div', {'class': 'RfADt'})
            price = prod_info.find_all('div', {'class': 'aBrP0'})
            discount_rate = prod_info.find_all('span', {'class': 'IcOsH'})
            sold = prod_info.find_all('span', {'class': '_1cEkb'})
            origin = prod_info.find_all('span', {'class': 'oa6ri'})
            moreinfo = prod_info.find_all('div', {'class': '_6uN7R'})

            if len(name) > 0: item_info['name'] = name[0].a.text
            if len(price) > 0: item_info['price'] = price[0].span.text
            if len(discount_rate) > 0: item_info['discount_rate'] = discount_rate[0].text
            if len(sold) > 0: item_info['sold'] = sold[0].span.text
            if len(origin) > 0: item_info['origin'] = origin[0].text
            if len(moreinfo) > 0 and len(moreinfo[0].find_all('i')) > 0:
                item_info['rating_count'] = moreinfo[0].find_all('span', {'class': 'qzqFw'})[0].text
                item_info['rating'] = [i['class'][1] for i in moreinfo[0].find_all('i')[:5]].count('Dy1nx')

            products.append(item_info)

    driver.close()

    laz_prod = pd.DataFrame(products)

    del url, ua, options, driver, soup, prod_items, item, prod_info, item_info, name, price, discount_rate, sold, origin, moreinfo

    return laz_prod

# Clean data laz 
def convert_to_num(text):
    text = text.lower()
    if 'k' in text:
        result = int(float(text.replace('k', '').strip()) * 1000)
    elif 'm' in text:
        result = int(float(text.replace('m', '').strip()) * 1000000)
    else:
        result = int(text.strip())

    return result

def format_price(text):
    return int(re.sub('\D', '', text).strip())

def format_sold(text):
    return convert_to_num(text.lower().replace('đã bán', ''))

def format_rating_count(text):
    return convert_to_num(text.strip('()'))

def format_discount_rate(text):
    return float(text.lower().replace('% off', '').strip())

# Scraping data
def search():
    search = input('What do you want to search?')
    confirm = input('Do you want to search this product? Y/n?')
    if confirm.lower() == 'y':
        print(f'Search: {search}')
        tiki_prod = tiki_search(search)
        laz_prod = laz_search(search)

        tiki = tiki_prod.copy()
        tiki = tiki[['id', 'name', 'price', 'original_price', 'discount', 'discount_rate', 'rating_average', 'review_count', 'origin']]

        laz = laz_prod.copy()
        laz['price'] = laz['price'].fillna('0').apply(format_price)
        laz['sold'] = laz['sold'].fillna('0').apply(format_sold)
        laz['rating_count'] = laz['rating_count'].fillna('0').apply(format_rating_count)
        laz['rating_average'] = laz['rating'].fillna('0').astype('float')
        laz['review_count'] = laz['rating_count']
        laz['discount_rate'] = laz['discount_rate'].fillna('0').apply(format_discount_rate)
        laz['original_price'] = laz['price'] / (1 - (laz['discount_rate'] / 100))
        laz['original_price'] = laz['original_price'].astype(int)
        laz['discount'] = laz['original_price'] - laz['price']

        data = pd.concat(
            [
                tiki[['id', 'name', 'price', 'original_price', 'discount', 'discount_rate', 'rating_average', 'review_count', 'origin']],
                laz[['id', 'name', 'price', 'original_price', 'discount', 'discount_rate', 'rating_average', 'review_count', 'origin']]
            ]
            # , axis=0
            # , ignore_index=True
            , keys=['tiki', 'laz']
            )
        
        print('Status: 202 OK')
        return data
    elif confirm.lower() == 'n':
        print('Exit')
        return
    else:
        print('Confirm error. Exit')
        return