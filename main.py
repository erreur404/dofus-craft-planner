import logging

from flask import Flask
from flask import render_template, request, send_from_directory, jsonify
from flaskwebgui import FlaskUI # import FlaskUI

from os import getcwd, system, popen
import sys
from pathlib import Path

from persistance import Persistance
from util import datafus_search as data

logging.info("create Flask server")
app = Flask(__name__)
logging.info("create UI window")
ui = FlaskUI(app, maximized=True, start_server="flask") # add app and parameters

static = Path("static")

logging.info("loading recipies and user data")
persistance = Persistance()


logging.info("defining server routes")
@app.route("/")
def hello():
    print(f"send {static/'main.html'}")
    return send_static('main.html')

@app.route("/api/searchable")
def get_searchable():
    return jsonify(data.get_searchables())

@app.route("/api/item_details/<id>")
def get_item_details(id):
    return jsonify(data.get_by_id(id))

def _get_crafts(df):
    res = {'crafts': [], 'total':[]}
    used_ingredients = {}
    # for each craft
    for _, craft in df.iterrows():
        logging.info(craft)
        # get the recipe
        item_to_craft = data.get_by_id(craft["item_id"])
        ingredients = data.get_ingredients(item_to_craft)
        # initialye the return object
        craft_json = {
            'item': item_to_craft,
            'item_price': persistance.get_price(craft.item_id),
            'quantity': craft.quantity,
            'crafted': craft.crafted,
            'ingredients': [],
            'buy_price': 0,
            'resources_value': 0,
        }
        # for each ingredient in the recipe
        for ing in ingredients:
            ing_id = ing["item"]["id"]
            if ing_id not in used_ingredients:
                used_ingredients[ing_id] = 0

            # how much of A is needed to craft x Bs
            needed = ing["quantity"] * max(0, craft["quantity"]-craft["crafted"])
            # how much of A do we own, and is not required by another craft
            owned = max(0, persistance.get_quantity(ing_id)-used_ingredients[ing_id])
            # how much one unit of the ingredient costs
            ing_price = persistance.get_price(ing_id)
            craft_json["ingredients"].append({
                'needed': needed,
                'owned': owned,
                'item_id': ing_id,
                'item_name': ing["item"]["name"],
                'item_price': ing_price,
                'set_price': ing_price*needed,
            })
            # compute the total cost of the craft
            craft_json["buy_price"] += ing_price*max(0, needed-owned)
            craft_json["resources_value"] += ing_price*needed
            # count how much of each ingredient we already required for all crafts (will be substracted from inventory and used for the total list)
            used_ingredients[ing_id] += needed
        res["crafts"].append(craft_json)
    for ing in used_ingredients:
        item = data.get_by_id(ing)
        needed = used_ingredients[ing]
        owned = persistance.get_quantity(ing)
        unit_price = persistance.get_price(ing)
        res["total"].append({
            'item': item,
            'item_price': unit_price,
            'needed': needed,
            'owned': owned,
            'buy_cost': unit_price * max(0, needed-owned)
        })
    return res

@app.route("/api/crafts", methods=["GET"])
def get_crafts():
    logging.info(f"computing { len(persistance.crafts) } crafts")
    res = _get_crafts(persistance.crafts)
    return jsonify(res)

@app.route("/api/crafts", methods=["POST"])
def add_craft():
    payload = request.json
    item = data.get_by_id(payload["item_id"])
    logging.info(item)
    if ("craft" in item and len(item["craft"]) > 0):
        persistance.craft_add(item, int(payload["quantity"]))
    return "ok"

@app.route("/api/crafts/<id>", methods=["DELETE"])
def delete_craft(id):
    item = data.get_by_id(id)
    logging.info(f"delete craft {item['name']}")
    persistance.craft_delete(item)
    return "ok"

@app.route("/api/crafts/<id>", methods=["POST"])
def do_craft(id):
    item = data.get_by_id(id)
    logging.info(f"do one craft {item['name']}")
    ingredients = _get_crafts(persistance.craft_df_of(item, 1, 0))
    logging.info(ingredients)
    ingredients = ingredients["total"]
    persistance.craft_one(item, ingredients)
    return "ok"

@app.route("/api/crafts/rentability", methods=["GET"])
def computeCraftsPrices():
    craftable = list(filter(lambda x: "craft" in x and len(x["craft"]) > 0, data.get_all_items()))
    priced_items = persistance.inventory[persistance.inventory.item_price > 0]
    priced_items_ids = list(priced_items["item_id"])
    craftable_with_price = list(filter(lambda x: x["id"] in priced_items_ids, craftable))
    craft_rentability = list(map(lambda item: _get_crafts(persistance.craft_df_of(item, 1, 0)) , craftable_with_price))
    print(craft_rentability[0])
    print(craft_rentability[0]["crafts"])
    print(craft_rentability[0]["crafts"][0])
    craft_rentability = list(map(lambda craft: {
        'item': craft["crafts"][0]["item"],
        'item_price': round(craft["crafts"][0]["item_price"]),
        'buy_price': round(craft["crafts"][0]["buy_price"]),
        'resources_value': round(craft["crafts"][0]["resources_value"]),
    }, craft_rentability))
    return jsonify(craft_rentability)

@app.route("/api/operations")
def get_operations():
    return jsonify(persistance.operations.to_dict(orient="records"))

@app.route("/api/operations/buy", methods=['POST'])
def buy_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.buy_item(item, int(payload["price"]), int(payload["quantity"]))
    return "bought"

@app.route("/api/operations/sell", methods=['POST'])
def sell_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.sell_item(item, int(payload["price"]), int(payload["quantity"]), payload["note"])
    return "sold"

@app.route("/api/operations/<id>/confirm", methods=["POST"])
def confirm_operations(id):
    persistance.operations.loc[persistance.operations.op_id == id, "sell_confirmed"] = True
    return "confirmed"

@app.route("/api/operations/<id>", methods=["DELETE"])
def delete_operations(id):
    persistance.operations = persistance.operations[persistance.operations.op_id != id]
    return "deleted"

@app.route("/api/inventory")
def get_inventory():
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/inventory/editQuantity", methods=['POST'])
def edit_inventory():
  payload = request.json
  persistance.set_quantity(data.get_by_id(payload["id"]), int(payload["quantity"]))
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/inventory/editPrice", methods=['POST'])
def edit_price():
  payload = request.json
  persistance.set_price(data.get_by_id(payload["id"]), int(payload["price"]))
  return "edited"

@app.route("/api/inventory/resetZeros", methods=['POST'])
def reset_zeros():
    logging.debug("flooring the inventory")
    logging.debug("\n" + str(persistance.inventory[persistance.inventory.quantity < 0]))
    persistance.inventory.quantity = persistance.inventory.apply(lambda row: max(0, row["quantity"]), axis=1)
    return "reset"

@app.route("/api/save", methods=['POST'])
def force_save():
    persistance.save()
    return "saved"

@app.route("/version", methods=["GET"])
def get_version():
    git_status = popen("git status")
    git_log = popen("git log")
    return (git_status.read() + "\n\n" + git_log.read()).replace('<', '[').replace('>', ']').replace('\n', '<br/>')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(static, path)

def open_default_browser():
    p = sys.platform
    logging.info(f"you are running on {p}")

    if p.startswith("win32"):
        system('explorer "http://localhost:5648"')
    elif p.startswith("darwin"):
        system('open http://localhost:5648')
    elif p.startswith("linux"):
        system('sensible-browser http://localhost:5648')

if __name__ == "__main__":
    logging.info("starting default browser")
    open_default_browser()
    logging.info(f"starting app at {getcwd()}")
    app.run(debug=True, port=5648)  # for debug

    #  ui.run()
