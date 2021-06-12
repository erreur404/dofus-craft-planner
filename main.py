import logging

from flask import Flask
from flask import render_template, request, send_from_directory, jsonify
from flaskwebgui import FlaskUI # import FlaskUI

from os import getcwd
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
    ingredients = _get_crafts(persistance.crafts[persistance.crafts.item_id == int(id)])
    logging.info(ingredients)
    ingredients = ingredients["total"]
    persistance.craft_one(item, ingredients)
    return "ok"

@app.route("/api/operations")
def get_operations():
    return jsonify(persistance.operations.to_dict(orient="records"))

@app.route("/api/operations/buy", methods=['POST'])
def buy_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.buy_item(item, int(payload["price"]), int(payload["quantity"]))
    return get_inventory()

@app.route("/api/operations/sell", methods=['POST'])
def sell_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.sell_item(item, int(payload["price"]), int(payload["quantity"]), payload["note"])
    return get_inventory()

@app.route("/api/operations/<id>/confirm", methods=["POST"])
def confirm_operations(id):
    persistance.operations.loc[persistance.operations.op_id == id, "sell_confirmed"] = True
    return "confirmed"

@app.route("/api/inventory")
def get_inventory():
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/inventory/editQuantity", methods=['POST'])
def edit_inventory():
  payload = request.json
  persistance.set_quantity(payload["id"], int(payload["quantity"]))
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/inventory/editPrice", methods=['POST'])
def edit_price():
  payload = request.json
  persistance.set_price(data.get_by_id(payload["id"]), int(payload["price"]))
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/save", methods=['POST'])
def force_save():
  persistance.save()
  return "saved"

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(static, path)



if __name__ == "__main__":
    logging.info(f"starting app at {getcwd()}")
    #  app.run(debug=True)  # for debug
    ui.run()
