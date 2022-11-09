import json
import requests
import pymysql
import re

from thread_with_return import ThreadWithReturnValue


def lambda_handler(event, context):
    """
    Entry point into API.

    Query the database before making the relevant API calls.

    If no records are found:

        Call api.postcodes.io/postcodes/<postcode_to_search>
        and if valid, extract constituency, longitude and latitude.

        Longitude and latitude as query params in the following APIs:
        - api.postcodes.io (Nearest Postcodes)
        - data.police.uk (Crime Statistics)
        
        If records are found from the API calls, save them to the database
        and return to the frontend.

    Otherwise:

        Prepare the data into respective dictionaries
        and return to the frontend.



    """
    nearest_postcode_list = []
    crime_stats_list = []
    planning_perms_list = []

    postcode = ''.join(event['rawQueryString'].split('=')[1])

    db_query = query_db(postcode)

    if not db_query:
        PIO_URL = 'https://api.postcodes.io/postcodes/{}'.format(postcode)

        # Query PlanIt API
        pp_res = requests.get(PIO_URL)
        pp_res = json.loads(pp_res.content)

        if pp_res['status'] != 404:

            data = pp_res['result']
            postcode = data['postcode']
            constituency = data['parliamentary_constituency']

            longitude = data['longitude']
            latitude = data['latitude']

            db_insert_attempt = add_postcode_to_db(postcode, constituency, longitude, latitude)

            if db_insert_attempt:

                thread1 = ThreadWithReturnValue(target=get_nearest_postcodes, args=(longitude, latitude, postcode,))
                thread2 = ThreadWithReturnValue(target=get_crime_stats, args=(longitude, latitude, postcode,))
                thread3 = ThreadWithReturnValue(target=get_planning_perms, args=(longitude, latitude, postcode,))

                thread1.start()
                thread2.start()
                thread3.start()

                nearest_postcodes = thread1.join()
                crime_stats = thread2.join()
                planning_perms = thread3.join()

                if planning_perms:
                    for item in planning_perms:
                        planning_perms_obj = {}

                        planning_perms_obj['address'] = item[1]
                        planning_perms_obj['application_type'] = item[4]
                        planning_perms_obj['description'] = item[0]
                        planning_perms_obj['url'] = item[2]
                        planning_perms_obj['status'] = item[3]

                        planning_perms_list.append(planning_perms_obj)


                for item in crime_stats:
                    crime_stat_obj = {}

                    crime_stat_obj['category'] = item[0]
                    crime_stat_obj['location'] = item[1]
                    crime_stat_obj['outcome_status'] = item[2]

                    crime_stats_list.append(crime_stat_obj)

                for item in nearest_postcodes:
                    nearest_postcode_obj = {}

                    nearest_postcode_obj['postcode'] = item[0]

                    nearest_postcode_list.append(nearest_postcode_obj)


                body = {
                    'postcode': postcode,
                    'planning_perms': planning_perms_list,
                    'crime_stats': crime_stats_list,
                    'nearest_postcodes': nearest_postcode_list,
                    'constituency': constituency,
                    'longitude': longitude,
                    'latitude': latitude
                }

                return {
                    "statusCode": 200,
                    "body": json.dumps(body)

                }

        else:
            return {
                "statusCode": 404
            }
    else:

        for item in db_query['planning_perms'][0]:
            planning_perms_obj = {}

            planning_perms_obj['address'] = item[1]
            planning_perms_obj['application_type'] = item[2]
            planning_perms_obj['description'] = item[3]
            planning_perms_obj['url'] = item[4]
            planning_perms_obj['status'] = item[5]

            planning_perms_list.append(planning_perms_obj)

        for item in db_query['crime_stats'][0]:
            crime_stat_obj = {}

            crime_stat_obj['category'] = item[1]
            crime_stat_obj['location'] = item[2]
            crime_stat_obj['outcome_status'] = item[3]

            crime_stats_list.append(crime_stat_obj)

        for item in db_query['nearest_postcodes'][0]:
            nearest_postcode_obj = {}

            nearest_postcode_obj['postcode'] = item[0]

            nearest_postcode_list.append(nearest_postcode_obj)

        postcode = db_query['postcode']
        constituency = db_query['constituency']
        longitude = db_query['longitude']
        latitude = db_query['latitude']

        body = {
            "postcode": postcode,
            "planning_perms": planning_perms_list,
            "crime_stats": crime_stats_list,
            "nearest_postcodes": nearest_postcode_list,
            "longitude": longitude,
            "latitude": latitude,
            "constituency": constituency
        }

        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }


def query_db(postcode) -> dict:
    """
    Query the database for postcode sent via AWS API Gateway
    Returns all stored records for a given postcode, if they exist.
    Otherwise return None.
    """

    conn, cursor = connect_to_db()

    # First query - Search for postcode
    query = 'SELECT * FROM postcode_info WHERE postcode="{}";'.format(postcode)

    cursor.execute(query)
    result = cursor.fetchall()
    longitude = None
    latitude = None

    if result:
        nearest_postcodes = []
        planning_perms = []
        crime_stats = []

        postcode = result[0][0]
        constituency = result[0][1]
        longitude = result[0][3]
        latitude = result[0][4]

        # Query DB for crime stats
        cs_query = '''
            SELECT * FROM crime_stat WHERE pid='{}'
            
        '''.format(postcode)

        cursor.execute(cs_query)
        result = cursor.fetchall()
        crime_stats.append(result)

        # Query DB for planning permissions
        pp_query = '''
            SELECT * FROM planning_perm WHERE pid='{}' 
        '''.format(postcode)

        cursor.execute(pp_query)
        result = cursor.fetchall()
        planning_perms.append(result)

        # Query DB for nearest postcodes
        np_query = '''
            SELECT * FROM nearest_postcode WHERE pid='{}'
        '''.format(postcode)

        cursor.execute(np_query)
        result = cursor.fetchall()
        nearest_postcodes.append(result)


        conn.close()

        return {
            "crime_stats": crime_stats,
            "planning_perms": planning_perms,
            "nearest_postcodes": nearest_postcodes,
            "longitude": longitude,
            "latitude": latitude,
            "constituency": constituency,
            "postcode": postcode
        }

    else:
        conn.close()
        return None


def add_postcode_to_db(postcode, constituency, longitude, latitude):
    """
    Adds the postcode, constituency, longitude and latitude data
    to the database, for a given postcode.
    """

    formatted_postcode = remove_whitespace(postcode)

    conn, cursor = connect_to_db()

    query = '''
        INSERT INTO postcode_info (postcode, constituency, longitude, latitude)
        VALUES ("{}", "{}", "{}", "{}");
    '''.format(formatted_postcode, constituency, longitude, latitude)

    try:
        cursor.execute(query)
        conn.commit()
        conn.close()
        return True
    except pymysql.Error as e:
        conn.close()
        return 'Error adding postcode to database: {}'.format(e)


def add_nearest_postcodes_to_db(postcodes):
    """
    Add the nearest postcodes to the database.

    Database insert statement is made within a for loop,
    with each record being inserted into the database upon
    each iteration.
    """
    conn, cursor = connect_to_db()

    db_entry_success = False

    for postcode, original_postcode in postcodes:

        formatted_postcode = remove_whitespace(original_postcode)

        query = '''
        INSERT INTO nearest_postcode (postcode, pid)
        VALUES ("{}", "{}") ON DUPLICATE KEY UPDATE postcode = "{}";
    '''.format(postcode, formatted_postcode, postcode)

        try:
            cursor.execute(query)
            conn.commit()
            db_entry_success = True
        except pymysql.Error as e:
            db_entry_success = False
            conn.close()
            print('Error adding nearest postcode to database: {}'.format(e))

    if db_entry_success:
        return True


def add_crime_stats_to_db(stats):
    """
    Add a given postcode's crime statistic to the database.

    Database insert statement is made within a for loop,
    with each record being inserted into the database upon
    each iteration.
    """

    conn, cursor = connect_to_db()

    for category, area, outcome, postcode in stats:
        formatted_postcode = remove_whitespace(postcode)
        query = '''
            INSERT INTO crime_stat (category, name, outcome_status, pid)
            VALUES ("{}", "{}", "{}", "{}");
         '''.format(category, area, outcome, formatted_postcode)

        try:
            cursor.execute(query)
            conn.commit()
        except pymysql.Error as e:
            print('Error adding crime stats to db: {}'.format(e))
    return conn


def add_planning_perms_to_db(planning_perms):
    """
    Add a given postcode's planning permissions to the database.

    Database insert statement is made within a for loop,
    with each record being inserted into the database upon
    each iteration.
    """

    conn, cursor = connect_to_db()

    for desc, address, url, status, original_postcode in planning_perms:
        formatted_postcode = remove_whitespace(original_postcode)
        query = '''
            INSERT INTO planning_perm (address, description, url, status, pid)
            VALUES ("{}", "{}", "{}", "{}", "{}");
        '''.format(address, desc, url, status, formatted_postcode)

        try:
            cursor.execute(query)
            conn.commit()
        except pymysql.Error as e:
            print('Error adding planning perms to db: {}'.format(e))
    return conn


def get_nearest_postcodes(long, lat, original_postcode):
    """
    Make API call to api.postcodes.io, using longitude and
    latitude as query params.

    If records are found, add them to the database and return
    the data.
    """

    postcodes = []

    URL = 'http://api.postcodes.io/postcodes?lon={}&lat={}'.format(long, lat)

    res = requests.get(URL)
    res = json.loads(res.content)

    if res['status'] != 404:
        for item in res['result']:
            if item['postcode'] != original_postcode:
                postcodes.append((item['postcode'], original_postcode))

        db_insert_attempt = add_nearest_postcodes_to_db(postcodes)
        return postcodes

    else:
        return {
            "statusCode": 404
        }


def get_crime_stats(long, lat, original_postcode):
    """
    Make API call to data.police.uk, using longitude and
    latitude as query params.

    If records are found, add them to the database and return
    the data.
    """

    URL = 'https://data.police.uk/api/crimes-street/all-crime?lat={}&lng={}&limit=10'.format(
        lat, long)
    crime_stats = []

    res = requests.get(URL)
    res = json.loads(res.content)

    if res:
        for index, item in enumerate(res):
            if index < 10:
                category = item['category']
                area = item['location']['street']['name']
                outcome = None
                if item['outcome_status']:
                    outcome = item['outcome_status']['category']

                crime_stats.append((category, area, outcome, original_postcode))

        db_insert_attempt = add_crime_stats_to_db(crime_stats)
        db_insert_attempt.close()

        return crime_stats
    else:
        return None


def get_planning_perms(original_postcode):
    """
    Make API call to api.propertydata.co.uk, using longitude and
    latitude as query params.

    If records are found, add them to the database and return
    the data.
    """
    planning_perms = []

    URL = 'https://api.propertydata.co.uk/planning?key=NFUWSROEZG&postcode={}'.format(
        original_postcode)

    try:
        res = requests.get(URL)
        res = json.loads(res.content)

        for item in res['data']['planning_applications']:
            desc = item['proposal']
            address = item['address']
            url = item['url']
            status = item['decision']['text']

            planning_perms.append(
                (
                    desc,
                    address,
                    url,
                    status,
                    original_postcode
                )
            )

        db_insert_attempt = add_planning_perms_to_db(planning_perms)
        db_insert_attempt.close()

        return planning_perms
    except TypeError as e:
        return False


def remove_whitespace(string):
    """
    Utility function to remove whitespace from postcode string.
    """
    return re.sub(r'\s+', '', string)


def connect_to_db():
    """
    Connect to database and return the connection and cursor.
    """
    db_conn = pymysql.connect(
        host='<host_url>',
        user='<db_user>',
        password='<db_pass>',
        database='<db_name>',
        ssl={'disable_tls': True}
    )

    cursor = db_conn.cursor()

    return db_conn, cursor