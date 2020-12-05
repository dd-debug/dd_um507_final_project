
#################################
##### Name: Jiadong Chen ########
##### Uniqname: jiadongc ########
#################################

import requests
import json
import sqlite3
from bs4 import BeautifulSoup
import secrets
import plotly.graph_objs as go
import plotly.figure_factory as ff

yelp_api_key = secrets.API_KEY
mapbox_token = secrets.MAPBOX_TOKEN
headers = {"Authorization": "Bearer " + yelp_api_key}
CACHE_FILE_NAME = 'cache.json'
CACHE_DICT = {}


def construct_unique_key(baseurl, params):
    ''' constructs a key that is guaranteed to uniquely and
    repeatably identify an API request by its baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs

    Returns
    -------
    string
        the unique key as a string
    '''
    connector = "_"
    params_list = []
    for e in params:
        params_list.append(f'{e}_{params[e]}')
    params_list.sort()
    key_str = baseurl + connector + connector.join(params_list)
    return key_str


def make_api_request(baseurl, params):
    '''Make a request to the Web API using the baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dictionary
        A dictionary of param:value pairs

    Returns
    -------
    dict
        the data returned from making the request in the form of
        a dictionary
    '''
    response = requests.get(baseurl, headers=headers, params=params)
    return response.json()


def make_api_request_with_cache(baseurl, params):
    '''Check the cache for a saved result for this baseurl+params:values
    combo. If the result is found, return it. Otherwise send a new
    request, save it, then return it.

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        The parameters to search for

    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
    key_str = construct_unique_key(baseurl, params)
    if key_str in CACHE_DICT:
        print("Using Cache")
        return CACHE_DICT[key_str]
    else:
        print("Fetching")
        CACHE_DICT[key_str] = make_api_request(baseurl, params)
        save_cache(CACHE_DICT)
        return CACHE_DICT[key_str]


def get_yelp_bussiness_search(city_name, term="coffee"):
    ''' search for cafes bussiness information in a city

    Parameters
    ----------
    city_name: string
        name of a city
    term: string
        term to search

    Returns
    -------
    dict
        query information dict
    '''
    yelp_url = "https://api.yelp.com/v3/businesses/search"
    params = {"location": city_name,
              "term": term,
              "limit": 50}
    yelp_business_dict = make_api_request_with_cache(yelp_url, params)
    return yelp_business_dict


def scrape_state_url():
    ''' scrape states and cities' url from the url. (crawling)

    Returns
    -------
    string
        url of the states and cities
    '''
    scrap_url = "https://www.britannica.com/topic/list-of-cities-and-towns-in-the-United-States-2023068/additional-info"
    response_text = make_url_request_using_cache(scrap_url, CACHE_DICT)
    soup = BeautifulSoup(response_text, 'html.parser')
    state_url = soup.find("a", class_="tab")["href"]
    return ("https://www.britannica.com" + state_url)


def build_state_cities_dict():
    ''' Make a dictionary that maps state name to cities name

    Returns
    -------
    dict
        key is a state name and value is the cities names
    '''
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
    '''Check the cache for a saved result for this url. If the result is found,
     return it. Otherwise send a new request, save it, then return it.

    Parameters
    ----------
    url: string
        The URL for the html
    cache: dict
        The cache with saved data

    Returns
    -------
    string
        the results of the query as a dictionary loaded from cache
    '''
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
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary

    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache


def save_cache(cache):
    ''' Saves the current state of the cache to disk

    Parameters
    ----------
    cache: dict
        The dictionary to save

    '''
    cache_file = open(CACHE_FILE_NAME, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()


def save_city_table(states_and_cities):
    ''' Save cities into database

    Parameters
    ----------
    states_and_cities: dict
        The dict of states, the key is state's name, the values are selected cities
    '''
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
    '''a business

    Instance Attributes
    -------------------
    city: string
        the city the business in

    name: string
        the name of the business

    address: string
        address of the business

    lat: int
        lattitude of the business

    lon: int
        longitude of the business

    zipcode: int
        the zip-code of the business

    price: string
        price level of the business

    image_url: string
        url of image of the business

    rating: float
        rating of the business

    review_count: int
        review number of the business
    '''
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
        self.save_business_table() #automatically save the business in table

    def info(self):
        '''return the business information'''
        return self.name + "(%s,%s)" % (
        self.rating, self.price) + ": " + self.address + ", " + self.city + ", " + self.zipcode

    def save_business_table(self):
        ''' Save the business into database
        '''
        conn = sqlite3.connect("final_project_db.sqlite")
        cur = conn.cursor()
        query = '''SELECT Id FROM Cities WHERE Cities.City= "%s"''' % self.city
        result = cur.execute(query).fetchall()
        conn.close()
        if len(result) == 0:
            cityId = ""
        else:
            cityId = result[0][0]
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
        info_list = [self.name, self.city, cityId, self.address + ", " + self.zipcode,
                     self.lat, self.lon, self.price, self.image_url,
                     self.rating, self.review_count]
        cur.execute(add_business, info_list)
        conn.commit()


def try_buss(dic, key):
    ''' if dic has key, return dic[key], else return "".

    Parameters
    ----------
    dic: string
        a city name
    yelp_business_dict: dict
        businesses dict from api query

    Returns
    -------
    list
        list of Businesses objects
    '''
    try:
        return dic[key]
    except:
        return ""


def build_buss_objs_from_dict(user_city, yelp_business_dict):
    ''' build Business objects from a list of api businesses information

    Parameters
    ----------
    user_city: string
        a city name
    yelp_business_dict: dict
        businesses dict from api query

    Returns
    -------
    list
        list of Businesses objects
    '''
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


def get_busi_db_info(props, params=None):
    ''' get business information from database

    Parameters
    ----------
    props: list
        a list of property strings to query, e.g. ["rating"]
    params: dict
        parameters pass into database query, e.g. {"city":"Ann Arbor"}

    Returns
    -------
    list
        Business property information that meets the parameters
    '''
    conn = sqlite3.connect("final_project_db.sqlite")
    cur = conn.cursor()
    real_props = ""
    for i in range(len(props)):
        real_props += "b.{}".format(props[i]) + ", "
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


def get_aver_info_db(props_str, params=None):
    ''' give the average info of cafes of a city

    Parameters
    ----------
    props_str: string
        property string to calculate info, e.g. "rating"
    params: dict
        parameters pass into database query, e.g. {"city":"Ann Arbor"}

    Returns
    -------
    string
        average rating
    '''
    result = get_busi_db_info([props_str], params=params)
    result = [e[0] for e in result]
    aver_info = sum(result) / len(result)
    res = "*" * len("Average %s of the city is %s" % (props_str, aver_info))
    res += "\n"
    res += "Average %s of %s city is %s" % (props_str, params["City"], aver_info)
    res += "\n"
    res += "*" * len("Average %s of the city is %s" % (props_str, aver_info))
    return res


def get_best_busi_based_on_rating_review(params=None):
    ''' give the best cafe of a city based on highest rating,
    then highest review numbers

    Parameters
    ----------
    params: dict
        parameters pass into database query, e.g. {"city":"Ann Arbor"}

    Returns
    -------
    string
        name and address of best cafe.
    '''
    result = get_busi_db_info(["rating", "review_number",
                               "Name", "City", "Address"], params=params)
    result = sorted(result, key=lambda x: (x[0], x[1]), reverse=True)
    result_str = "*" * 40 + "\n"
    result_str += "The best coffee we recommend: \n" \
                  "{}: {}, \n" \
                  "rating: {}, review number: {} " \
                  "".format(result[0][2], result[0][3] + ", " + result[0][4], result[0][0], result[0][1])
    result_str += "\n" + "*" * 40
    return result_str


def input_state_name(states_and_cities):
    ''' interactive: let user input a choice from "exit" or valid name of a state.
    When get a invalid input, input operation will be required until get a valid one.
    When get "exit", the program exits.

    Parameters
    ----------
    states_and_cities: dict
        The dict of states, the key is state's name, the values are selected cities

    Returns
    -------
    string
        a state's name
    '''
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
    ''' interactive: let user input a choice from "exit" or valid number of cities number.
    When get a invalid input, input operation will be required until get a valid one.

    Parameters
    -------
    cities: list

    Returns
    -------
    int
        a valid number of cities
    '''
    cities_numbers = list(range(1, len(cities) + 1))
    cities_numbers = [str(i) for i in cities_numbers]
    while True:
        num = input(
            '''To see different Cafes, please enter a city number from [%s, %s] or "exit": ''' % (1, len(cities)))
        if num.lower() == "exit":
            exit()
        elif num not in cities_numbers:
            print("[Error] Enter proper city number from [%s, %s]" % (1, len(cities)))
            print()
        else:
            break
    return int(num) - 1


def input_user_choice():
    ''' interactive: let user input a choice from "exit" or valid number of a choice.
    When get a invalid input, input operation will be required until get a valid one.

    Returns
    -------
    int
        a valid number of user choice
    '''
    print("-" * len("Data processing or visualization"))
    print("Data processing or visualization")
    print("-" * len("Data processing or visualization"))
    print("1. Average rating of the cafes we queried.")
    print("2. The best cafe we recommend.")
    print("3. Cafes businesses map in this city.")
    print("4. Kernel density distribution of rating of cafes in this city.")
    print("5. Scatter plot of rating and review number of cafes in this city.")
    print("6. Plot price pie chart based on rating.")
    print("7. Choose a new city.")
    right_choice = list(range(1, 8))
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
    ''' display the list of cities of a state

    Parameters
    ----------
    cities: list
        cities of a state
    '''
    print("-" * len("Major Cities in this State."))
    print("Major Cities in this State.")
    print("-" * len("Major Cities in this State."))
    for i in range(len(cities)):
        print(str(i + 1) + ". " + cities[i])


def display_businesses(yelp_buss_objs):
    ''' display the list of Bussiness objects

    Parameters
    ----------
    cities: list
        a list of Businesses objects
    '''
    print("-" * len("Major Cafes in this city."))
    print("Major Cafes in this city.")
    print("-" * len("Major Cafes in this city."))
    for i in range(len(yelp_buss_objs)):
        print(str(i + 1) + ". " + yelp_buss_objs[i].info())


def map_businesses(user_city):
    ''' show cafes of a city in map

    Parameters
    ----------
    user_city: str
        a city name

    Return
    ----------
    fig: plotly figure object
        a plotly figure
    '''
    text_list = []
    lat_list = []
    lon_list = []
    ra_list = []
    for bu in get_busi_db_info(["Name", "City", "Address", "Latitude", "Longitude", "rating"], {"City": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[5]))
        lat_list.append(bu[3])
        lon_list.append(bu[4])
        ra_list.append(bu[5])

    ave_lat = sum(lat_list) / len(lat_list)
    ave_lon = sum(lon_list) / len(lon_list)
    fig = go.Figure(
        go.Scattermapbox(
            lat=lat_list,
            lon=lon_list,
            mode='markers',
            marker=go.scattermapbox.Marker(size=15, color=ra_list,
                                           opacity=0.5,
                                           colorbar=dict(title="ratings"),
                                           colorscale="rdylbu"),
            text=text_list,
        ))

    layout = dict(
        autosize=True,
        hovermode='closest',
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_token,
            bearing=0,
            center=go.layout.mapbox.Center(lat=ave_lat,
                                           lon=ave_lon),
            pitch=0,
            zoom=10),
        plot_bgcolor="black",
        paper_bgcolor="cornsilk",
        width=1200,
        height=700
    )

    fig.update_layout(layout)

    return fig


def display_print(text):
    ''' stress the text with symbol *

    Parameters
    ----------
    text: string
        a string to print
    '''
    print("*" * len(text))
    print(text)
    print("*" * len(text))


def kde_rating(user_city):
    ''' show kde distribution of ratings

    Parameters
    ----------
    user_city: str
        a city name

    Return
    ----------
    fig: plotly figure object
        a plotly figure
    '''
    text_list = []
    ra_list = []
    for bu in get_busi_db_info(["Name", "City", "Address", "rating"], {"City": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[3]))
        ra_list.append(bu[3])
    fig = ff.create_distplot([ra_list], ['rating'], bin_size=.2,
                             show_hist=False, show_rug=False)
    fig.update_xaxes(title_text="Ratings", ticks="inside")
    fig.update_yaxes(title_text="Kernel Density", ticks="inside")
    fig.update_layout(font=dict(size=20, family='Calibri', color='black'),
                      template="ggplot2",
                      title={'text': "Rating distribution"})
    return fig

def review_rating_scatter(user_city):
    ''' show scatter plot, rating versus to review numbers

    Parameters
    ----------
    user_city: str
        a city name

    Return
    ----------
    fig: plotly figure object
        a plotly figure
    '''
    text_list = []
    ra_list = []
    re_list = []
    for bu in get_busi_db_info(["Name", "City", "Address", "rating", "review_number"], {"City": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[3]))
        ra_list.append(bu[3])
        re_list.append(bu[4])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ra_list,y=re_list,
                    mode="markers",
                    marker=dict(
                        size=15,
                        color = ra_list,
                        colorbar=dict(title="ratings"),
                        colorscale="rdylbu"),
                    text=text_list,
                    textposition="top center",
                    opacity=0.8
                    ))
    fig.update_xaxes(title_text="Ratings", ticks="inside")
    fig.update_yaxes(title_text="Review numbers", ticks="inside")
    fig.update_layout(font=dict(size=20, family='Calibri', color='black'),
                      # template="ggplot2",
                      title={'text': "Review number and rating scatter plot"})
    return fig

def review_rating_scatter(user_city):
    ''' show scatter plot, rating versus to review numbers

    Parameters
    ----------
    user_city: str
        a city name

    Return
    ----------
    fig: plotly figure object
        a plotly figure
    '''
    text_list = []
    ra_list = []
    re_list = []
    for bu in get_busi_db_info(["Name", "City", "Address", "rating", "review_number"], {"City": user_city}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[3]))
        ra_list.append(bu[3])
        re_list.append(bu[4])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ra_list,y=re_list,
                    mode="markers",
                    marker=dict(
                        size=15,
                        color = ra_list,
                        colorbar=dict(title="ratings"),
                        colorscale="rdylbu"),
                    text=text_list,
                    textposition="top center",
                    opacity=0.8
                    ))
    fig.update_xaxes(title_text="Ratings", ticks="inside")
    fig.update_yaxes(title_text="Review numbers", ticks="inside")
    fig.update_layout(font=dict(size=20, family='Calibri', color='black'),
                      # template="ggplot2",
                      title={'text': "Review number and rating scatter plot"})
    return fig

def pie_price_highest_rating(user_city, rating = 5.0):
    ''' give the price pie chart with same rating

    Parameters
    ----------
    user_city: str
        a city name
    rating: float
        a rating score of businesses

    '''
    text_list = []
    ra_list = []
    price_list = []
    for bu in get_busi_db_info(["Name", "City", "Address", "rating", "price"],
                               {"City": user_city, "rating": rating}):
        text_list.append("{} ({}): {}, rating: {}".format(bu[0], bu[1], bu[2], bu[3]))
        ra_list.append(bu[3])
        price_list.append(bu[4])
    fig = go.Figure()
    if len(price_list) == 0:
        display_print("Oops, no cafe has %s rating." % rating)
        return None
    result = {}
    for key in price_list:
        result[key] = result.get(key, 0) + 1
    labels = list(result.keys())
    num_labels = []
    for la in labels:
        if len(la) == 0:
            num_labels.append("no price information")
        else:
            num_labels.append("level "+str(len(la)))
    values = list(result.values())
    fig.add_trace(go.Pie(labels=num_labels, values=values))
    fig.show()

def input_rating():
    ''' get the input of user between 0 and 5 with error check.

    Return
    ----------
    float
        The user input
    '''
    while True:
        try:
            a = input("Please input a rating you are interested in [0.0,5.0], e.g. 4.5: ")
            if a.lower() == "exit":
                exit()
            a = float(a)
            if a >= 0 and a <= 5:
                return a
                break
            else:
                print("Input is not in range! Try again")
        except:
            print("Error happens! Try again!")

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
        while user_choice != 7:
            user_choice = input_user_choice()
            params = {"City":user_city}
            if user_choice == 1:
                print(get_aver_info_db("rating",params))
            if user_choice == 2:
                print(get_best_busi_based_on_rating_review(params))
            if user_choice == 3:
                display_print("Cafes businesses map of %s city has generated!" % user_city)
                fig = map_businesses(user_city)
                fig.show()
            if user_choice == 4:
                display_print("Kde plot of rating in %s city" % user_city)
                fig = kde_rating(user_city)
                fig.show()
            if user_choice == 5:
                display_print("Scatter plot of review number versus rating in %s city" % user_city)
                fig = review_rating_scatter(user_city)
                fig.show()
            if user_choice == 6:
                rat = input_rating()
                pie_price_highest_rating(user_city, rating=rat)