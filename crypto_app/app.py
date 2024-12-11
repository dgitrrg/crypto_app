from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)


API_KEY = "add_api_key_here"

class Node:
    def __init__(self, data, metric):
        self.data = data
        self.metric = metric
        self.next = None

class OrderedLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None

    def append_sorted(self, data, metric):
        new_node = Node(data, metric)
        if self.head is None:
            self.head = new_node
            self.tail = new_node
            return
        
        if metric > self.head.metric:
            new_node.next = self.head
            self.head = new_node
            return
        if metric <= self.tail.metric:
            self.tail.next = new_node
            self.tail = new_node
            return

        current = self.head
        while current.next and current.next.metric >= metric:
            current = current.next
        new_node.next = current.next
        current.next = new_node

    def get_top(self, count):
        results = []
        current = self.head
        while current and len(results) < count:
            results.append(current.data)
            current = current.next
        return results

class Coin:
    def __init__(self, name, market_cap, volume, mentions):
        self.name = name
        self.market_cap = market_cap  
        self.volume = volume  
        self.mentions = mentions 

class CoinGraph:
    def __init__(self):
        self.edges = {}  
    
    def add_coin(self, coin):
        if coin.name not in self.edges:
            self.edges[coin.name] = 0  
    
    def edge_count(self, coins):
        for coin in coins:
            self.add_coin(coin) 
            
            if coin.market_cap > 1_000_000: 
                self.edges[coin.name] += 1
            
            if coin.volume > 500_000: 
                self.edges[coin.name] += 1
            
            if coin.mentions > 1000: 
                self.edges[coin.name] += 1

    def display_edges(self):
        print("Edge Counts for Each Coin:")
        for coin, count in self.edges.items():
            print(f"{coin}: {count} edges")

def fetch_latest_coins():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": API_KEY}
    params = {"start": 1, "limit": 100, "convert": "USD", "sort": "date_added"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        raise Exception(f"Error fetching data: {response.status_code}, {response.text}")

def analyze_coins(coins):
    linked_list = OrderedLinkedList()

    for coin in coins:
        try:
            name = coin.get("name")
            symbol = coin.get("symbol")
            price = coin["quote"]["USD"].get("price", 0)
            market_cap = coin["quote"]["USD"].get("market_cap", 0)
            volume_24h = coin["quote"]["USD"].get("volume_24h", 0)
            volume_1h = coin["quote"]["USD"].get("volume_change_1h", 0)
            circulating_supply = coin.get("circulating_supply", 0)
            total_supply = coin.get("total_supply", 1)    

            
            if not name or not symbol or total_supply == 0:
                print(f"Skipping coin due to missing data: {coin}")
                continue

            
            fully_diluted_price = price * total_supply
            volume_to_marketcap_ratio = volume_24h / market_cap if market_cap else 0
            circulating_ratio = circulating_supply / total_supply if total_supply else 0
            risk_metric = (
                market_cap * (volume_to_marketcap_ratio + volume_1h)
            )

            linked_list.append_sorted(
                {"name": name, "symbol": symbol, "price": price, "market_cap": market_cap},
                risk_metric,
            )
        except KeyError as e:
            print(f"KeyError processing coin {coin.get('name', 'Unknown')}: {e}")
        except Exception as e:
            print(f"Error processing coin {coin.get('name', 'Unknown')}: {e}")

    return linked_list

def create_graph(top_coins):
    coin_objects = [
        Coin(
            name=coin["name"],
            market_cap=coin["market_cap"],
            volume=coin.get("volume_24h", 0),
            mentions=coin.get("mentions", 0)
        )
        for coin in top_coins
    ]

    coin_graph = CoinGraph()
    coin_graph.edge_count(coin_objects)

    sorted_by_edges = sorted(
        top_coins,
        key=lambda x: (-coin_graph.edges.get(x["name"], 0), -x["market_cap"])
    )

    return sorted_by_edges

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fetch-coins", methods=["GET"])
def fetch_and_analyze():
    try:
        coins = fetch_latest_coins()
        analyzed_list = analyze_coins(coins)
        top_20 = analyzed_list.get_top(20)

        high_risk = create_graph(top_20[:10])
        ultra_high_risk = create_graph(top_20[10:])

        return jsonify(
            {"high_risk": high_risk, "ultra_high_risk": ultra_high_risk}
        )
    except Exception as e:
        print(f"Error in fetching or analyzing coins: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
