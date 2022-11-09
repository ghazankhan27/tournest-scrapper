from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
import json

cred = credentials.Certificate(
    "./tournest-62f85-firebase-adminsdk-h5nci-da412043ff.json"
)

app = firebase_admin.initialize_app(cred, {"databaseURL": "/"})


def get_all_cities_pakistan():

    cities_file = open("pk.json", "r", encoding="utf-8")

    data = json.load(cities_file)

    cities = []

    for city in data:
        cities.append(city["city"])

    return cities


def get_data_from_db():
    db = firestore.client(app)
    collection = db.collection("History")
    docs = collection.get()
    for doc in docs:
        x = doc.to_dict()
        print(x)


def add_tour_to_db(tour):

    print("Adding to firebase", tour["title"])
    db = firestore.client(app)

    itinerary = tour["itinerary"]

    tour.pop("itinerary")

    print("Adding Tour")
    update_time, tour_ref = db.collection("Tours").add(tour)

    tour_id = tour_ref.id

    print("Adding itineraries")
    for iti in itinerary:

        update_time, iti_ref = db.collection("Itinerary").add(
            {"day": iti["day"], "description": iti["description"], "tour": tour_id}
        )

        iti_id = iti_ref.id

        i = 1

        print("Adding itineraries items")
        for item in iti["items"]:

            obj = {
                "Itinerary": iti_id,
                "description": item,
                "image": iti["img"],
                "itemno": i,
                "title": iti["description"],
            }

            i += 1

            db.collection("Itinerary_Item").add(obj)


options = webdriver.FirefoxOptions()
options.add_argument("--headless")

driver = webdriver.Firefox(options=options)


def wait_for_element(by, selector):

    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )

        return element

    except:
        raise Exception("Could not find element:", selector)


def scrape_gozayaan(place):

    try:

        tours_information_list = []

        print("Getting website: Gozayaan")
        driver.maximize_window()
        driver.get("https://www.gozayaan.com/?search=tour")

        search_bar = wait_for_element(By.CSS_SELECTOR, "div.tour-search.bar")

        search_bar.click()

        search_input = wait_for_element(By.ID, "searchString")

        print("Sending search query")
        search_input.clear()
        search_input.send_keys(place)

        location_list = wait_for_element(By.CLASS_NAME, "location-list")

        location_suggestions = location_list.find_elements(By.CLASS_NAME, "location")

        print("Clicking first suggestion")
        location_suggestions[0].click()

        print("Clicking search button")
        search_button = wait_for_element(By.CLASS_NAME, "search-btn")

        search_button.click()

        print("Waiting for tours to show up")
        wait_for_element(By.CLASS_NAME, "tour-card-wrapper")

        print("Get all tours")
        tours_list = driver.find_elements(By.CLASS_NAME, "tour-card-wrapper")

        tour_names = []

        for tour in tours_list:

            name_element = tour.find_element(By.TAG_NAME, "h4")

            name = name_element.get_attribute("innerText")

            tour_names.append(name)

        for name in tour_names:

            to_click_element = None

            wait_for_element(By.CLASS_NAME, "tour-card-wrapper")

            tours_list = driver.find_elements(By.CLASS_NAME, "tour-card-wrapper")

            for tour in tours_list:

                name_element = tour.find_element(By.TAG_NAME, "h4")

                _name = name_element.get_attribute("innerText")

                if name == _name:

                    to_click_element = tour

                    break

            to_click_element.click()

            print("Visited", name)

            wait_for_element(By.CLASS_NAME, "tour-title")

            source = driver.page_source

            soup = BeautifulSoup(str(source), "lxml")

            title = str(soup.select_one(".tour-title").get_text()).strip()
            days = str(soup.select(".summary-point")[0].find("span").get_text()).strip()
            overview = str(soup.find("div", id="overview").div.p.get_text()).strip()
            description = str(
                soup.find("div", id="tour-description").div.div.get_text()
            ).strip()
            img = soup.find("div", id="gallery").div.find("img").get("src")
            location = str(soup.find("a", class_="location-link").get_text()).strip()
            url = driver.current_url
            price = str(
                soup.find("div", class_="price-info-text").h6.get_text()
            ).strip()

            itinerary_tab = driver.find_element(By.ID, "itinerary")

            driver.execute_script(
                'document.getElementById("itinerary").scrollIntoView({block:"center"})'
            )

            itinerary_tab.click()

            itinerary_details = wait_for_element(By.ID, "itinerary-details")

            it_days = itinerary_details.find_element(
                By.CLASS_NAME, "day-tabs"
            ).find_elements(By.CLASS_NAME, "day-title")

            current_day = 1

            it_day_items = []

            for day in it_days:
                day.click()

                html = driver.find_elements(By.CSS_SELECTOR, "div.itinerary-preview")

                for ht in html:

                    inner_html = ht.get_attribute("innerHTML")

                    tiny_soup = BeautifulSoup(str(inner_html), "lxml")

                    description_it = str(
                        tiny_soup.find("h2", class_="tour-title").get_text()
                    ).strip()

                    check_img_it = tiny_soup.find("img")

                    if check_img_it == None:
                        img_it = ""
                    else:
                        img_it = str(check_img_it.get("src")).strip()

                    day_num = current_day

                    it_items_list = []

                    it_items = tiny_soup.find_all("li")

                    for it_item in it_items:

                        item = str(it_item.get_text()).strip()

                        it_items_list.append(item)

                it_obj = {
                    "day": day_num,
                    "description": description_it,
                    "img": img_it,
                    "items": it_items_list,
                }

                it_day_items.append(it_obj)

                current_day += 1

                sleep(1)

            obj = {
                "title": title,
                "days": days,
                "short_description": overview,
                "description": description,
                "image": img,
                "location": location,
                "url": url,
                "price": price,
                "type": "gozayaan",
                "itinerary": it_day_items,
            }

            add_tour_to_db(obj)

            tours_information_list.append(obj)

            back_button = driver.find_element(By.CLASS_NAME, "back-to-see-all")

            back_button = back_button.find_element(By.TAG_NAME, "span")

            back_button.click()

    except Exception as error:
        print(error)


def main():

    cities = get_all_cities_pakistan()

    for city in cities:
        try:
            print("Scraping " + city)
            scrape_gozayaan(city)
        except:
            print("Could not scrape " + city)
            continue

    driver.close()


main()
