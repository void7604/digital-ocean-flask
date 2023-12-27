from flask import Flask, request
import pymysql
import time
import requests
import json

app = Flask(__name__)

# PostgreSQL configurations
mysql_config = {
    'database': 's63710_thunder-bot-db',
    'user': 'u63710_uIrOdxIt6z',
    'password': '=35Xirnq@MJViaun!1DG.XE8',
    'host': 'gamesfra2.bisecthosting.com',
    'port': 3306
}

schema = '`s63710_thunder-bot-db`'
webhookURL = "https://discord.com/api/webhooks/1068896789513654292/vG0KxeAGtLH3fap_vIctSkxDewCHzhhaiCLhRPn6ulSyckGTpjiQKYuy_YNJCGE6x2Ip"

def create_oribos_exchange_link(region, realm_name, item_id):
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    return f"https://oribos.exchange/#{region.lower()}-{fixed_realm_name}/{item_id}"

def get_coin_values(num):
    if num >= 0:
        gold = num // 10000
        gold_str = "{:,}".format(gold).replace(",", " ")  # Replace comma with space
        return "**{}**<:Gold:1069562618496417852>".format(gold_str)
    else:
        num = abs(num)
        gold = num // 10000
        gold_str = "{:,}".format(gold).replace(",", " ")  # Replace comma with space
        return "**-{}**<:Gold:1069562618496417852>".format(gold_str)

def extract_item_info_from_ingame_link(item_link):
    start_id = item_link.find("|Hitem:") + 7
    end_id = item_link.find(":", start_id)
    item_id = item_link[start_id:end_id]

    start_name = item_link.find("[") + 1
    end_name = item_link.find("]", start_name)
    item_name = item_link[start_name:end_name]

    if "battlepet:" in item_link:
        start_species_id = item_link.find("battlepet:") + 10
        end_species_id = item_link.find(":", start_species_id)
        species_id = item_link[start_species_id:end_species_id]
        return (item_name, f"82800-{species_id}")
    else:
        return (item_name, item_id)

def build_discord_message(transaction, server, region, price, dbregion, thundervalue, key):
    item_name, item_id = extract_item_info_from_ingame_link(key)
    if transaction == 'buy':
        return [{
            "title": f"{item_name}",
            "description": f"**Item sniped !!** <t:{int(time.time())}:f>\nPrice Paid: {get_coin_values(price)}\nRegionMarketAvg: {get_coin_values(dbregion)}\nEstimated Value: {get_coin_values(thundervalue)}",
            "url": f"{create_oribos_exchange_link(region, server, item_id)}",
            "color": 11311379,
            "author": {
                "name": f"{server}-{region}"
            }
        }]
    elif transaction == 'sale':
        return [{
            "title": f"{item_name}",
            "description": f"**Item sold !!** <t:{int(time.time())}:f>\nPrice : {get_coin_values(price)}\nRegionMarketAvg: {get_coin_values(dbregion)}\nEstimated Value: {get_coin_values(thundervalue)}",
            "url": f"{create_oribos_exchange_link(region, server, item_id)}",
            "color": 11311379,
            "author": {
                "name": f"{server}-{region}"
            }
        }]
    else:
        return "Invalid auction type"

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    conn = pymysql.connect(**mysql_config)
    data = request.get_json()
    accountID = data.get('accountID')
    timestamp = int(time.time())
    region = data.get('region')
    bot_type = data.get('type')
    sales = data.get('sales')
    expenses = data.get('expenses')


    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {schema}.dashboard WHERE accountID={accountID}")
    result = cur.fetchone()

    if result:
        cur.execute(f"UPDATE {schema}.dashboard SET timestamp={timestamp}, sales={sales}, expenses={expenses} WHERE accountID={accountID}")
    else:
        cur.execute(f"INSERT INTO {schema}.dashboard (accountID, timestamp, region, bot_type, sales, expenses) VALUES ({accountID}, {timestamp}, '{region}', '{bot_type}', {sales}, {expenses})")
    conn.commit()
    cur.close()
    conn.close()

    return 'Request logged successfully'

@app.route('/transactions', methods=['POST'])
def transactions():
    # Extract the data from the request  TODO: ! check the right query and table
    data = request.get_json()

    # Create a cursor object to execute SQL queries
    conn = pymysql.connect(**mysql_config)
    cur = conn.cursor()

    # Insert the data into the database
    connectionID = data['connectionID']
    servername = data['servername']
    region = data['region']
    timestamp = int(time.time())
    transaction = data['type']
    itemkey = data['itemkey']
    price = data['price']
    dbregion = data['dbregion']
    thundervalue = data['thundervalue']
    transactor = data['transactor']

    query = f"INSERT INTO {schema}.auctionlog (connectionID,region,timestamp,transaction,itemkey,price,dbregion,thundervalue,transactor) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
    cur.execute(query, (connectionID,region,timestamp,transaction,itemkey,price,dbregion,thundervalue,transactor))

    # Commit the changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

    if (transaction == 'sale' and price > 200000000) or (transaction == 'buy' and dbregion > 250000000):
        # Send a Discord webhook message
        message = build_discord_message(transaction, servername,region, price, dbregion, thundervalue, itemkey)
        payload = {
            "content": '',
            "embeds": message,
            "attachments": []
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(webhookURL, data=json.dumps(payload), headers=headers)
        if response.status_code != 204:
            print(f"Failed to send Discord webhook message: {response.status_code} {response.text}")
    else : return 'Auction logged successfully'

    # Return a response to the client
    return 'Auction logged successfully'

@app.route("/TSM", methods=['POST', 'GET', 'DELETE'])
def TSM():
    conn = pymysql.connect(**mysql_config)
    cur = conn.cursor()

    if request.method == "POST":
        body = request.get_json()
        accountID = body['accountID']
        region = body['region']
        data = json.dumps(body['data'])  # Convert to JSON string
        timestamp = int(time.time())

        cur.execute(f"SELECT * FROM {schema}.`tsm` WHERE accountID = %s", (accountID,))
        result = cur.fetchone()

        if result:
            cur.execute(f"UPDATE {schema}.`tsm` SET data = %s, timestamp = %s WHERE accountID = %s",
                        (data, timestamp, accountID))
        else:
            cur.execute(f"INSERT INTO {schema}.`tsm` (accountID, region, timestamp, data) VALUES (%s, %s, %s, %s)",
                        (accountID, region, timestamp, data))

        conn.commit()
        cur.close()
        conn.close()

        return f"TSM Data uploaded for {accountID}"

    elif request.method == "GET":
        region = request.args.get("region")
        accountID = request.args.get("accountID")
        if region:
            cur.execute(f"SELECT * FROM {schema}.`tsm` WHERE region = {region}")
        elif accountID:
            cur.execute(f"SELECT * FROM {schema}.`tsm` WHERE accountID = {accountID}")
        rows = cur.fetchall()
        result = []
        for row in rows:
            print(row[0])
            result.append({
                "accountID": row[0],
                "data": json.loads(row[3]),
                "timestamp": row[1]
            })
        cur.close()
        conn.close()
        return json.dumps(result)

    elif request.method == "DELETE":
        region = request.args.get("region")
        account = request.args.get("accountID")
        response = ""
        if region:
            cur.execute(f"DELETE FROM {schema}.`tsm` WHERE region = %s", (region,))
            response = f"TSM Data deleted for region {region}"
        elif account:
            cur.execute(f"DELETE FROM {schema}.`tsm` WHERE accountID = %s", (account,))
            response = f"Task deleted for accountID {account}"
        conn.commit()
        cur.close()
        conn.close()
        return response

@app.route("/Tasks", methods=['POST', 'GET', 'DELETE'])
def Tasks():
    conn = pymysql.connect(**mysql_config)
    cur = conn.cursor()

    if request.method == "POST":
        body = request.get_json()
        accountID = body['accountID']
        region = body['region']
        data = json.dumps(body['data'])  # Convert to JSON string
        timestamp = int(time.time())

        cur.execute(f"SELECT * FROM {schema}.`tasks` WHERE accountID = %s", (accountID,))
        result = cur.fetchone()

        if result:
            cur.execute(f"UPDATE {schema}.`tasks` SET data = %s, timestamp = %s WHERE accountID = %s",
                        (data, timestamp, accountID))
        else:
            cur.execute(f"INSERT INTO {schema}.`tasks` (accountID, region, timestamp, data) VALUES (%s, %s, %s, %s)",
                        (accountID, region, timestamp, data))

        conn.commit()
        cur.close()
        conn.close()

        return f"Tasks uploaded for {accountID}"

    elif request.method == "GET":
        region = request.args.get("region")
        accountID = request.args.get("accountID")
        if region:
            print(f"SELECT * FROM {schema}.`tasks` WHERE region = {region}")
            cur.execute(f"SELECT * FROM {schema}.`tasks` WHERE region = {region}")
        elif accountID:
            cur.execute(f"SELECT * FROM {schema}.`tasks` WHERE accountID = {accountID}")
        rows = cur.fetchall()
        result = []
        for row in rows:
            print(row[0])
            result.append({
                "accountID": row[0],
                "data": json.loads(row[3]),
                "timestamp": row[1]
            })
        cur.close()
        conn.close()
        return json.dumps(result)

    elif request.method == "DELETE":
        region = request.args.get("region")
        account = request.args.get("accountID")
        response = ""
        if region:
            cur.execute(f"DELETE FROM {schema}.`tasks` WHERE region = %s", (region,))
            response = f"Tasks deleted for region {region}"
        elif account:
            cur.execute(f"DELETE FROM {schema}.`tasks` WHERE accountID = %s", (account,))
            response = f"Task deleted for accountID {account}"
        conn.commit()
        cur.close()
        conn.close()
        return response

@app.route("/PriceCache", methods=['POST', 'GET'])
def PriceCache():
    conn = pymysql.connect(**mysql_config)
    cur = conn.cursor()

    if request.method == "POST":
        body = request.get_json()
        accountID = body['accountID']
        region = body['region']
        data = json.dumps(body['data'])  # Convert to JSON string
        cur.execute(f"SELECT * FROM {schema}.`price_cache` WHERE accountID = {accountID}")
        result = cur.fetchone()
        if result:
            cur.execute(f"UPDATE {schema}.`price_cache` SET data = %s WHERE accountID = %s",
                        (data, accountID))
        else:
            cur.execute(f"INSERT INTO {schema}.`price_cache` (accountID, region, data) VALUES (%s, %s, %s)",
                        (accountID, region, data))
        conn.commit()
        cur.close()
        conn.close()
        return f"PriceCache uploaded for {accountID}"

    elif request.method == "GET":
        region = request.args.get("region")
        cur.execute(f"SELECT * FROM {schema}.`price_cache` WHERE region = {region}")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "accountID": row[0],
                "data": json.loads(row[1]),
            })
        cur.close()
        conn.close()
        return json.dumps(result or {})
    
    elif request.method == "DELETE":
        region = request.args.get("region")
        response = ""
        cur.execute(f"DELETE FROM {schema}.`price_cache` WHERE region = %s", (region,))
        response = f"priceCache deleted for region {region}"
        conn.commit()
        cur.close()
        conn.close()
        return response

@app.route("/Restock", methods=['POST', 'GET'])
def Restock():
    conn = pymysql.connect(**mysql_config)
    cur = conn.cursor()

    if request.method == "POST":
        body = request.get_json()
        region = body['region']
        data = json.dumps(body['data'])  # Convert to JSON string
        cur.execute(f"SELECT * FROM {schema}.`restock` WHERE region = {region}")
        result = cur.fetchone()
        if result:
            cur.execute(f"UPDATE {schema}.`restock` SET data = %s WHERE region = %s",
                        (data, region))
        else:
            cur.execute(f"INSERT INTO {schema}.`restock` (region, data) VALUES (%s, %s)",
                        (region, data))
        conn.commit()
        cur.close()
        conn.close()
        return f"Restock uploaded for {region}"

    elif request.method == "GET":
        region = request.args.get("region")
        cur.execute(f"SELECT * FROM {schema}.`restock` WHERE region = {region}")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "region": row[0],
                "data": json.loads(row[1]or  {}) ,
            })
        cur.close()
        conn.close()
        return json.dumps(result or {}) 
    
    elif request.method == "DELETE":
        region = request.args.get("region")
        response = ""
        cur.execute(f"DELETE FROM {schema}.`restock` WHERE region = %s", (region,))
        response = f"restock deleted for region {region}"
        conn.commit()
        cur.close()
        conn.close()
        return response

@app.route("/Hello",methods=['GET'])
def Hello():
    return "Hello World!"

@app.route("/")
def hello_world():
    return render_template("index.html")


