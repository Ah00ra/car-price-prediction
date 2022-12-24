from bs4 import BeautifulSoup
from selenium import webdriver
import jdatetime
import logging
import sqlite3
import time

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

driver = webdriver.Firefox()


def scroll_it(scroll_limit):
    """use selenium to scroll it
    then driver.page_source will be used for scraping
    """

    url = "https://bama.ir/car?priced=1"
    driver.get(url)
    screen_height = driver.execute_script("return window.screen.height;")

    i = 1
    while 1:
        time.sleep(1)
        driver.execute_script(f"window.scrollTo(0, {screen_height}*{i});")
        i += 1
        if i == scroll_limit:
            break


items = []


def fetch_data():
    """scrape data and append it to items list"""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for item in soup.select(".bama-ad"):
        try:
            name = item.select_one(".bama-ad__title").text.strip().split("، ")[1]
            price = item.select_one(".bama-ad__price").text.strip().replace(",", "")
            mileage = (
                item.select_one("span:nth-child(3)")
                .text.strip()
                .split()[0]
                .replace(",", "")
            )
            if mileage == "کارکرده":
                # ignore those with unknown mileage
                continue

            if (
                mileage == "کارکرد"
            ):  # zero mileages was written in persian, convert it to "0"
                mileage = mileage.replace("کارکرد", "0")

            model = item.select_one(
                ".bama-ad__detail-row span:nth-child(1)"
            ).text.strip()
            if model[0] == "2":  # BUG
                # convert Gregorian to Jalali
                model = jdatetime.date.fromgregorian(
                    day=1, month=1, year=int(model)
                ).year

            items.append([name, int(price), int(model), int(mileage)])

        except Exception as e:
            logging.warning(e)

    logging.info(f"{len(items)} items fetched")


def write_data():
    written_data_count = 0
    """write items[] variable data into database
    ignore duplicated items"""

    con = sqlite3.connect("test.db")
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS car(name text, price int, model int, mileage int)"
    )

    for item in items:
        name = item[0]
        price = item[1]
        model = item[2]
        mileage = item[3]

        query = cur.execute(
            f"SELECT * FROM car WHERE name='{name}'\
            AND price='{price}' AND model='{model}'\
            AND mileage='{mileage}'"
        )

        if query.fetchone() is None:
            cur.execute("INSERT INTO car VALUES(?, ?, ?, ?)", item)
            written_data_count += 1

    logging.info(f"{written_data_count} items written into db")

    con.commit()
    con.close()


if __name__ == "__main__":
    scroll_it(scroll_limit=100)
    fetch_data()
    write_data()
