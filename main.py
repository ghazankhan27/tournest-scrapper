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
options.add_argument("--headless")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-running-insecure-content")

driver = webdriver.Firefox(options=options)
driver.set_window_size(1920, 1080)


def wait_for_element(by, selector):

    try:
        element = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((by, selector))
        )

        return element

    except:
        raise Exception("Could not find element:", selector)


def scrape_gozayaan(place):

    try:

        driver.get("https://www.gozayaan.com/?search=tour")

        print("Finding search bar")

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

        # Waiting for tours to show up
        tours = wait_for_element(
            By.CSS_SELECTOR, "div.tour-card > div.tour-card-wrapper"
        )

        if tours == None:
            raise Exception("Tours not found")

        print("Get all tours")

        # Get the total number of tours
        tours_list = driver.find_elements(
            By.CSS_SELECTOR, "div.tour-card > div.tour-card-wrapper"
        )

        # Go through a range of len(tours)
        for x in range(len(tours_list)):

            try:
                price = (
                    str(
                        tours_list[x]
                        .find_element(By.CSS_SELECTOR, "span.price-highlight")
                        .text
                    )
                    .split(" ")[1]
                    .replace(",", "")
                )
            except:
                print("No price for tour")
                continue

            # Clicking the tour
            tours_list[x].click()

            wait_for_element(By.CLASS_NAME, "tour-title")

            source = driver.page_source

            try:

                soup = BeautifulSoup(str(source), "lxml")

                title = str(soup.select_one(".tour-title").get_text()).strip()
                days = str(
                    soup.select(".summary-point")[0].find("span").get_text()
                ).strip()
                overview = str(soup.find("div", id="overview").div.p.get_text()).strip()
                description = str(
                    soup.find("div", id="tour-description").div.div.get_text()
                ).strip()
                img = soup.find("div", id="gallery").div.find("img").get("src")
                location = str(
                    soup.find("a", class_="location-link").get_text()
                ).strip()
                url = driver.current_url

                itinerary_tab = driver.find_element(By.ID, "itinerary")

                itinerary_tab.click()

                itinerary_details = wait_for_element(By.ID, "itinerary-details")

                it_days = itinerary_details.find_element(
                    By.CLASS_NAME, "day-tabs"
                ).find_elements(By.CLASS_NAME, "day-title")

                current_day = 1

                it_day_items = []

                for day in it_days:
                    day.click()

                    html = driver.find_elements(
                        By.CSS_SELECTOR, "div.itinerary-preview"
                    )

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
            except:
                print("Incomplete data in tour")
                continue

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

            driver.back()

            tours = wait_for_element(
                By.CSS_SELECTOR, "div.tour-card > div.tour-card-wrapper"
            )

            if tours == None:
                raise Exception("Tours not found")

            tours_list = driver.find_elements(
                By.CSS_SELECTOR, "div.tour-card > div.tour-card-wrapper"
            )

    except Exception as error:
        print(error)
        return


def scrape_booking(place):

    try:

        driver.get(
            "https://www.booking.com/index.en-gb.html?label=gen173nr-1BCAEoggI46AdIM1gEaLUBiAEBmAEJuAEXyAEP2AEB6AEBiAIBqAIDuAKzn8WbBsACAdICJDBmODE2ODlmLTg3Y2MtNGJhNi1iOWJiLWRjZDU2YmFhNDMwY9gCBeACAQ&sid=bfd7ba59bf28050f96132d870539fd2c&keep_landing=1&sb_price_type=total&"
        )

        print("Looking for search input")

        driver.get_screenshot_as_file("screenshot.png")

        search_bar = wait_for_element(By.ID, "ss")

        if search_bar == None:
            raise Exception("Couldn't find search bar")

        search_bar.clear()
        search_bar.send_keys(place)

        find_calender = wait_for_element(By.XPATH, "//div[@class='xp__dates-inner']")

        if find_calender == None:
            raise Exception("Couldn't find calendar")

        driver.find_element(By.XPATH, "//div[@class='xp__dates-inner']").click()
        days = driver.find_elements(By.XPATH, "//td[@role='gridcell']")

        if days == None:
            raise Exception("Couldn't find dates in the calender")

        print("Selecting dates")

        try:
            for i in range(len(days)):
                item = days[i]
                adjacent_item = days[i + 1]

                class_name = item.get_attribute("class")
                if "bui-calendar__date--today" in class_name:
                    item.click()
                    adjacent_item.click()
                    break

        except Exception as e:
            raise Exception("Could not click correct dates on calendar")

        search_button = driver.find_element(
            By.CSS_SELECTOR, "button.sb-searchbox__button"
        )

        if search_button == None:
            raise Exception("Could not find search button")

        search_button.click()

        next_page_exists = True

        while next_page_exists:

            property_list_item = wait_for_element(
                By.XPATH,
                "//div[@data-testid='property-card']//a[@data-testid='title-link']//div[1]",
            )

            if property_list_item == None:
                raise Exception("No hotels found")

            print("Getting list of properties")

            property_list_items = driver.find_elements(
                By.XPATH,
                "//div[@data-testid='property-card']//a[@data-testid='title-link']//div[1]",
            )
            property_list_links = driver.find_elements(
                By.XPATH,
                "//div[@data-testid='property-card']//a[@data-testid='title-link']",
            )
            property_list_images = driver.find_elements(
                By.XPATH, "//img[@data-testid='image']"
            )
            property_list_location = driver.find_elements(
                By.XPATH, "//span[@data-testid='address']"
            )
            property_list_price = driver.find_elements(
                By.XPATH, "//*[@data-testid='price-and-discounted-price']"
            )

            if (
                not len(property_list_items)
                == len(property_list_links)
                == len(property_list_images)
                == len(property_list_location)
                == len(property_list_price)
            ):
                raise Exception("Data is invalid")

            obj = {}

            try:
                for i in range(len(property_list_items)):
                    name = property_list_items[i]
                    img = property_list_images[i]
                    link = property_list_links[i]
                    location = property_list_location[i]
                    price = property_list_price[i]

                    obj["title"] = str(name.text).strip()
                    obj["img"] = str(img.get_attribute("src"))
                    obj["link"] = str(link.get_attribute("href"))
                    obj["location"] = str(location.text).strip()
                    obj["price"] = str(price.text).strip()
                    obj["type"] = "Booking.com"

                    add_hotel_to_db(obj)
            except:
                raise Exception("There was a problem geting data correctly")

            print("Checking if next button exists")

            next_button = driver.find_element(
                By.XPATH, "//button[@aria-label='Next page']"
            )

            if next_button == None:
                print("We are on the last page")
                next_page_exists = False

            next_button.click()

            loader = wait_for_element(By.XPATH, "//div[@data-testid='overlay-card']")

            EC.invisibility_of_element(loader)

            sleep(5)

    except Exception as error:
        print(error)
        return


def scrape_trips_pk(place):

    try:

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }

        res = requests.get(
            "https://www.trips.pk/tours/{place}".format(place=place),
            headers=headers,
        )

        soup = BeautifulSoup(res.text, "lxml")

        if soup.select_one("div.col-lg-9 > h2.h2Prop") != None:
            raise Exception("No Tours found")

        print("Grabbing tours")

        tours_exists = True
        current_page = 1

        while tours_exists:
            tours = soup.select("div#TourListContent > a")

            for tour in tours:

                title = tour.select_one("h4").text.strip()
                url = "https://www.trips.pk" + tour["href"]
                price = tour.select_one("div.package-price").text.split(" ")[1] + " PKR"
                days = tour.select_one("table.package-info td").text.strip()
                location = tour.select_one("table.package-info  td > span").text.strip()
                image = tour.select_one("div.package-tab-main-img > img")["src"]

                itenerary_items = []

                tour_source = requests.get(url, headers=headers)

                tour_soup = BeautifulSoup(tour_source.text, "lxml")

                description = tour_soup.select_one(
                    "div.package-detail-info div.package-detail > p"
                ).text.strip()

                try:
                    current_day = 1

                    itenerary = tour_soup.select("div.accordion-body")

                    for ite in itenerary:

                        it_items_list = []

                        it_items = ite.select("p")

                        for it_item in it_items:

                            if len(it_item.get_text()) <= 0:
                                continue

                            x = str(it_item).split("<br/>")
                            for s in x:
                                ran = BeautifulSoup(s, "lxml")
                                it_text = ran.get_text().strip()
                                if len(it_text) <= 0:
                                    continue
                                it_items_list.append(
                                    ran.get_text()
                                    .strip()
                                    .replace("&nbsp", "")
                                    .replace("&amp", "&")
                                )

                        it_obj = {
                            "day": current_day,
                            "description": "",
                            "img": "",
                            "items": it_items_list,
                        }

                        itenerary_items.append(it_obj)

                        current_day = current_day + 1

                except Exception as e:
                    print(e)
                    itenerary_items = []

                obj = {
                    "title": title,
                    "days": days,
                    "short_description": "",
                    "description": description,
                    "image": image,
                    "location": location,
                    "url": url,
                    "price": price,
                    "type": "trips.pk",
                    "itinerary": itenerary_items,
                }

                add_tour_to_db(obj)

            current_page = current_page + 1

            res = requests.get(
                "https://www.trips.pk/tours/{place}?PageNo={page_number}".format(
                    place=place, page_number=current_page
                ),
                headers=headers,
            )

            if soup.select_one("div.col-lg-9 > h2.h2Prop") != None:
                tours_exists = False
                raise Exception("No Tours found")

            print("Grabbing tours", current_page)

    except Exception as error:
        print(error)
        return


def main():

    cities = ["france"]

    for city in cities:
        print("Scraping " + city)
        print("/------------------Booking.com-----------------------------------/")
        scrape_booking(city)
        print("/------------------Gozayaan.com-----------------------------------/")
        scrape_gozayaan(city)
        print("/------------------Trips.pk-----------------------------------/")
        scrape_trips_pk(city)

    driver.close()


main()
