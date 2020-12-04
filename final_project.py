import requests
import json
import sqlite3
from bs4 import BeautifulSoup
import secrets

yelp_api_key = secrets.API_KEY

headers = {"Authorization": "Bearer " + yelp_api_key}
CACHE_FILE_NAME = 'cache.json'
CACHE_DICT = {}


def construct_unique_key(baseurl, params):
    connector = "_"
    params_list = []
    for e in params:
        params_list.append(f'{e}_{params[e]}')
    params_list.sort()
    key_str = baseurl + connector + connector.join(params_list)
    return key_str


def make_api_request(baseurl, params):
    response = requests.get(baseurl, headers=headers, params=params)
    return response.json()


def make_api_request_with_cache(baseurl, params):
    key_str = construct_unique_key(baseurl, params)
    if key_str in CACHE_DICT:
        print("Using Cache")
        return CACHE_DICT[key_str]
    else:
        print("Fetching")
        CACHE_DICT[key_str] = make_api_request(baseurl, params)
        save_cache(CACHE_DICT)
        return CACHE_DICT[key_str]

def get_yelp_bussiness_search(city_name, term = "coffee"):
    yelp_url = "https://api.yelp.com/v3/businesses/search"
    params = {"location": city_name,
              "term": term,
              "limit": 50}
    yelp_business_dict = make_api_request_with_cache(yelp_url, params)
    return yelp_business_dict


def scrape_state_url():
    scrap_url = "https://www.britannica.com/topic/list-of-cities-and-towns-in-the-United-States-2023068/additional-info"
    response_text = make_url_request_using_cache(scrap_url, CACHE_DICT)
    soup = BeautifulSoup(response_text, 'html.parser')
    state_url = soup.find("a", class_="tab")["href"]
    return ("https://www.britannica.com" + state_url)


def build_state_cities_dict():
    state_url = scrape_state_url()
    response_text = make_url_request_using_cache(state_url, CACHE_DICT)
    soup = BeautifulSoup(response_text, 'html.parser')
    soup_states = soup.find_all('h2', class_="h1")
    states = []
    for state in soup_states:
        states.append(state.find("a", class_="md-crosslink").text)
    states = [e.lower() for e in states]
    cities_by_states = soup.find_all("ul", class_="topic-list")
    cities_by_states_namelist = []
    for cities in cities_by_states:
        cities_list = []
        for city in cities:
            if city.text != "Napa":
                cities_list.append(city.find("a").text)
            else:
                cities_list.append('Napa')
        cities_by_states_namelist.append(cities_list)
    states_and_cities = dict(zip(states, cities_by_states_namelist))
    # for e in states_and_cities:
    #     print(e,'\n',states_and_cities[e])
    return states_and_cities


def make_url_request_using_cache(url, cache):
    if url in list(cache.keys()):  # the url is our unique key
        print("Using Cache")
        return cache[url]
    else:
        print("Fetching")
        # print(url)
        response = requests.get(url)
        cache[url] = response.text
        save_cache(cache)
        return cache[url]  # in both cases, we return cache[url]

def load_cache():
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache


def save_cache(cache):
    cache_file = open(CACHE_FILE_NAME, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()


def save_city_table(states_and_cities):
    try:
        create_city_table = '''
            CREATE TABLE "Cities" (
                "Id"        INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                "City"  TEXT NOT NULL,
                "State" TEXT NOT NULL
            );
        '''
        conn = sqlite3.connect("final_project_db.sqlite")
        cur = conn.cursor()
        cur.execute(create_city_table)
        add_city = "INSERT INTO Cities VALUES (NULL, ?, ?)"
        for state in states_and_cities:
            for city in states_and_cities[state]:
                cur.execute(add_city, (city, state))
        conn.commit()
    except:
        return None

class Business():
    def __init__(self, name=None, city=None, address=None,
                 lat=None, lon=None, zipcode=None, price=None,
                 image_url=None, rating=None, review_count=None):
        self.name = name
        self.city = city
        self.address = address
        self.lat = lat
        self.lon = lon
        self.zipcode = zipcode
        self.price = price
        self.image_url = image_url
        self.rating = rating
        self.review_count = review_count
        self.save_business_table()

    def info(self):
        return self.name + "(%s,%s)" % (self.rating, self.price) + ": " + self.address + ", " + self.city + ", " + self.zipcode

    def save_business_table(self):
        conn = sqlite3.connect("final_project_db.sqlite")
        cur = conn.cursor()
        query = '''SELECT Id FROM Cities WHERE Cities.City= "%s"''' % self.city
        result = cur.execute(query).fetchall()
        conn.close()
        if len(result) == 0:
            cityId=""
        else:
            cityId=result[0][0]
        create_business_table = '''
                CREATE TABLE IF NOT EXISTS "Businesses" (
                    "Id"        INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    "Name"  TEXT NOT NULL,
                    "City" TEXT NOT NULL,
                    "CityId" INTEGER NOT NULL,
                    "Address" TEXT NOT NULL,
                    "Latitude" REAL,
                    "Longitude" REAL,
                    "Price" TEXT NOT NULL,
                    "Image_url" TEXT NOT NULL,
                    "Rating" REAL,
                    "Review_number" INTEGER,
                    FOREIGN KEY (CityId) REFERENCES Cities (Id)
                );
            '''
        conn = sqlite3.connect("final_project_db.sqlite")
        cur = conn.cursor()
        cur.execute(create_business_table)
        add_business = "INSERT INTO Businesses VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        info_list = [self.name, self.city, cityId, self.address+", "+self.zipcode,
                     self.lat, self.lon, self.price, self.image_url,
                     self.rating, self.review_count]
        cur.execute(add_business, info_list)
        conn.commit()

def try_buss(dic,key):
    try:
        return dic[key]
    except:
        return ""

def build_buss_objs_from_dict(user_city, yelp_business_dict):
    buss_objs = []
    for bu in yelp_business_dict["businesses"]:
        if user_city.lower() == try_buss(try_buss(bu, "location"), "city").lower():
            attr_list = []
            attr_list.append(try_buss(bu, "name"))
            attr_list.append(try_buss(try_buss(bu, "location"), "city"))
            attr_list.append(try_buss(try_buss(bu, "location"), "address1"))
            attr_list.append(try_buss(try_buss(bu, "coordinates"), "latitude"))
            attr_list.append(try_buss(try_buss(bu, "coordinates"), "longitude"))
            attr_list.append(try_buss(try_buss(bu, "location"), "zip_code"))
            attr_list.append(try_buss(bu, "price"))
            attr_list.append(try_buss(bu, "image_url"))
            attr_list.append(try_buss(bu, "rating"))
            attr_list.append(try_buss(bu, "review_count"))
            buss_objs.append(Business(*attr_list))
    return buss_objs


def get_busi_db_info(props,params=None):
    '''props list
    params dict'''
    conn = sqlite3.connect("final_project_db.sqlite")
    cur = conn.cursor()
    real_props = ""
    for i in range(len(props)):
        real_props += "b.{}".format(props[i])+", "
    real_props = real_props[:-2]
    command = '''SELECT {} FROM Businesses as b'''.format(real_props)
    if params != None:
        keys = list(params.keys())
        for key in keys:
            if keys.index(key) == 0:
                command += ' WHERE {}="{}"'.format(key, params[key])
            else:
                command += ' AND {}="{}"'.format(key, params[key])
    command += ";"
    result = cur.execute(command).fetchall()
    conn.close()
    return result

def get_aver_info_db(props_str,params=None):
    result = get_busi_db_info([props_str],params=params)
    result = [e[0] for e in result]
    aver_info = sum(result)/len(result)
    res = "*"* len("Average %s of the city is %s" % (props_str, aver_info))
    res += "\n"
    res += "Average %s of %s city is %s" % (props_str, params["City"], aver_info)
    res += "\n"
    res += "*" * len("Average %s of the city is %s" % (props_str, aver_info))
    return res

def get_best_busi_based_on_rating_review(params=None):
    result = get_busi_db_info(["rating","review_number",
                               "Name","City","Address"], params=params)
    result = sorted(result, key=lambda x: (x[0], x[1]), reverse=True)
    result_str = "*"*40 + "\n"
    result_str += "The best coffee we recommend: \n" \
                 "{}: {}, \n" \
                 "rating: {}, review number: {} " \
                 "".format(result[0][2], result[0][3]+", "+result[0][4], result[0][0], result[0][1])
    result_str += "\n" + "*" * 40
    return result_str


def input_state_name(states_and_cities):
    states = list(states_and_cities.keys())
    while True:
        state_name = input('''Enter a state name (e.g. Michigan, michigan) or "exit": ''')
        if state_name.lower() == "exit":
            exit()
        elif state_name.lower() not in states:
            print("[Error] Enter proper state name")
            print()
        else:
            break
    return state_name


def input_city_number(cities):
    cities_numbers = list(range(1,len(cities)+1))
    cities_numbers = [str(i) for i in cities_numbers]
    while True:
        num = input('''To see different Cafes, please enter a city number from [%s, %s] or "exit": ''' % (1, len(cities)))
        if num.lower() == "exit":
            exit()
        elif num not in cities_numbers:
            print("[Error] Enter proper city number from [%s, %s]" % (1, len(cities)))
            print()
        else:
            break
    return int(num)-1

def input_user_choice():
    print("-" * len("Data processing or visualization"))
    print("Data processing or visualization")
    print("-" * len("Data processing or visualization"))
    print("1. Average rating of the cafes we queried.")
    print("2. The best cafe we recommend.")
    print("3. Data visualization.")
    print("4. Choose a new city.")
    right_choice = list(range(1,5))
    right_choice = [str(i) for i in right_choice]
    while True:
        num = input("Enter a choice to process/visualize data or 'exit':")
        if num.lower() == "exit":
            exit()
        elif num not in right_choice:
            print("[Error] Enter proper number from [%s, %s]" % (1, len(right_choice)))
            print()
        else:
            break
    return int(num)

def display_cities(cities):
    print("-"*len("Major Cities in this State."))
    print("Major Cities in this State.")
    print("-" * len("Major Cities in this State."))
    for i in range(len(cities)):
        print(str(i+1)+". "+cities[i])

def display_businesses(yelp_buss_objs):
    print("-"*len("Major Cafes in this city."))
    print("Major Cafes in this city.")
    print("-" * len("Major Cafes in this city."))
    for i in range(len(yelp_buss_objs)):
        print(str(i+1)+". "+yelp_buss_objs[i].info())

if __name__ == "__main__":

    CACHE_DICT = load_cache()
    states_and_cities = build_state_cities_dict()
    save_city_table(states_and_cities)

    while True:
        state_name = input_state_name(states_and_cities)
        cities = states_and_cities[state_name.lower()]
        display_cities(cities)
        city_num = input_city_number(cities)
        user_city = cities[city_num]

        yelp_business_dict = get_yelp_bussiness_search(user_city)
        yelp_buss_objs = build_buss_objs_from_dict(user_city, yelp_business_dict)
        display_businesses(yelp_buss_objs)

        user_choice = ""
        while user_choice != 4:
            user_choice = input_user_choice()
            params = {"City":user_city}
            if user_choice == 1:
                print(get_aver_info_db("rating",params))
            if user_choice == 2:
                print(get_best_busi_based_on_rating_review(params))
            if user_choice == 3:
                print("haha haimeixie")