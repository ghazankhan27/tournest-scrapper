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


def add_hotel_to_db(hotel):
    db = firestore.client(app)

    print("Adding {title} to db".format(title=hotel["title"]))

    db.collection("Hotels").add(hotel)


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
# options.add_argument("--headless")

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
        return


def scrape_booking(place):

    try:

        driver.maximize_window()

        driver.get(
            "https://www.booking.com/index.en-gb.html?label=gen173nr-1BCAEoggI46AdIM1gEaLUBiAEBmAEJuAEXyAEP2AEB6AEBiAIBqAIDuAKzn8WbBsACAdICJDBmODE2ODlmLTg3Y2MtNGJhNi1iOWJiLWRjZDU2YmFhNDMwY9gCBeACAQ&sid=bfd7ba59bf28050f96132d870539fd2c&keep_landing=1&sb_price_type=total&"
        )

        sleep(10)

        form = wait_for_element(By.ID, "frm")

        search_field = form.find_element(By.ID, "ss")

        search_field.click()

        search_field.clear()

        search_field.send_keys(place)

        wait_for_element(By.CSS_SELECTOR, "div.xp__dates.xp__group").click()

        wait_for_element(
            By.XPATH, "//td[@class='bui-calendar__date bui-calendar__date--today']"
        ).click()

        wait_for_element(
            By.XPATH,
            "//td[@class='bui-calendar__date bui-calendar__date--today bui-calendar__date--selected']/following-sibling::td",
        ).click()

        search_botton = driver.find_element(
            By.CSS_SELECTOR, "button.sb-searchbox__button"
        )

        search_botton.click()

        sleep(5)

        wait_for_element(By.XPATH, "//div[@data-testid='property-card']")

        list_of_properties = driver.find_elements(
            By.XPATH, "//div[@data-testid='property-card']"
        )

        for i in range(len(list_of_properties)):

            try:

                title = driver.find_element(
                    By.XPATH,
                    "(//div[@data-testid='property-card'])[{index}]//div[@data-testid='title']".format(
                        index=i + 1
                    ),
                ).text

                link = driver.find_element(
                    By.XPATH,
                    "(//div[@data-testid='property-card'])[{index}]//a[@data-testid='title-link']".format(
                        index=i + 1
                    ),
                ).get_attribute("href")

                location = driver.find_element(
                    By.XPATH,
                    "(//div[@data-testid='property-card'])[{index}]//span[@data-testid='address']".format(
                        index=i + 1
                    ),
                ).text

                price = driver.find_element(
                    By.XPATH,
                    "(//div[@data-testid='property-card'])[{index}]//span[@data-testid='price-and-discounted-price']".format(
                        index=i + 1
                    ),
                ).text

                img = driver.find_element(
                    By.XPATH,
                    "(//div[@data-testid='property-card'])[{index}]//img[@data-testid='image']".format(
                        index=i + 1
                    ),
                ).get_attribute("src")

            except Exception as e:
                print(e)
                continue

            obj = {
                "title": title,
                "link": link,
                "location": location,
                "price": price,
                "img": img,
                "type": "hotel",
            }

            add_hotel_to_db(obj)

    except Exception as error:
        print(error)
        return


def scrape_tours_pk(place):

    res = requests.get(
        "https://www.trips.pk/tours/search?keyword={keyword}".format(keyword=place),
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        },
    )

    soup = BeautifulSoup(res.text, "lxml")

    tours = soup.select("div#TourListContent > a")

    for tour in tours:

        title = tour.select_one("h4").text.strip()
        url = "https://www.trips.pk" + tour["href"]
        price = tour.select_one("div.package-price").text.split(" ")[1] + " PKR"
        days = tour.select_one("table.package-info td").text

        obj = {"title": title, "url": url, "price": price, "days": days}

        print(obj)


def main():

    cities = get_all_cities_pakistan()

    for city in cities:
        print("Scraping " + city)
        scrape_booking(city)
        scrape_gozayaan(city)
        scrape_tours_pk(city)

    driver.close()


main()
