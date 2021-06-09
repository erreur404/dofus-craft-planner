import logging

from flask import Flask
from flask import render_template, request, send_from_directory, jsonify
from flaskwebgui import FlaskUI # import FlaskUI

from os import getcwd
from pathlib import Path
from math import ceil

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

@app.route("/api/recipies")
def get_recipies():
    return []

@app.route("/api/searchable")
def get_searchable():
    return jsonify(data.get_searchables())

@app.route("/api/item_details/<id>")
def get_item_details(id):
    return jsonify(data.get_by_id(id))

@app.route("/api/buy", methods=['POST'])
def buy_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.buy_item(item, int(payload["price"]), int(payload["quantity"]))
    return get_inventory()

@app.route("/api/sell", methods=['POST'])
def sell_items():
    payload = request.json
    item = data.get_by_id(payload["id"])
    persistance.sell_item(item, int(payload["price"]), int(payload["quantity"]), payload["note"])
    return get_inventory()

@app.route("/api/operations")
def get_operations():
    return jsonify(persistance.operations.to_dict(orient="records"))

@app.route("/api/inventory")
def get_inventory():
  return jsonify(persistance.inventory.to_dict(orient="records"))

@app.route("/api/inventory/editQuantity", methods=['POST'])
def edit_inventory():
  payload = request.json
  persistance.inventory.loc[persistance.inventory.item_id == payload["id"], "quantity"] = int(payload["quantity"])
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
    app.run(debug=True)  # for debug
    #  ui.run()
