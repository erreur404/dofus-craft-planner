import logging
import pandas as pd
from os.path import exists


DB_FILE = "db.xlsx"
OPERATIONS_SHEET = "operations"
INVENTORY_SHEET = "inventory"
CRAFT_SHEET = "crafts"


class Persistance:
    def __init__(self):
        if exists(DB_FILE):
            logging.debug(f"DB file {DB_FILE} exists!")
            logging.debug(f"reading {DB_FILE}::sheet={OPERATIONS_SHEET} to Persistance.operations")
            self.operations = pd.read_excel(DB_FILE, sheet_name=OPERATIONS_SHEET)
            logging.debug(f"reading {DB_FILE}::sheet={INVENTORY_SHEET} to Persistance.inventory")
            self.inventory = pd.read_excel(DB_FILE, sheet_name=INVENTORY_SHEET)
            logging.debug(f"reading {DB_FILE}::sheet={CRAFT_SHEET} to Persistance.crafts")
            self.crafts = pd.read_excel(DB_FILE, sheet_name=CRAFT_SHEET)
        else:
            logging.debug(f"DB file {DB_FILE} not found")
            logging.debug(f"generating dataframes")
            self.operations = pd.DataFrame(columns=[
              "buy_or_sell",
              "item_name",
              "item_url",
              "item_id",
              "sell_confirmed",
              "item_price",
              "item_note",
              "quantity",
            ])
            self.inventory = pd.DataFrame(columns=[
              "item_name",
              "item_url",
              "item_id",
              "quantity",
              "item_price",
            ])
            self.crafts = pd.DataFrame(columns=[
              "item_name",
              "item_url",
              "quantity",
              "crafted",
            ])

    def save(self):
        writer = pd.ExcelWriter(DB_FILE, engine="xlsxwriter")
        logging.debug(f"saving Persistance.operations to {DB_FILE}::sheet={OPERATIONS_SHEET}")
        logging.debug(self.operations)
        self.operations.to_excel(writer, sheet_name=OPERATIONS_SHEET)
        logging.debug(f"saving Persistance.inventory to {DB_FILE}::sheet={INVENTORY_SHEET}")
        logging.debug(self.inventory)
        self.inventory.to_excel(writer, sheet_name=INVENTORY_SHEET)
        logging.debug(f"saving Persistance.crafts to {DB_FILE}::sheet={CRAFT_SHEET}")
        self.crafts.to_excel(writer, sheet_name=CRAFT_SHEET)
        writer.save()

    def buy_item(self, item, price, quantity):
        self.item_operation("buy", item, price, quantity)

    def sell_item(self, item, price, quantity, note):
        self.item_operation("sell", item, price, quantity, note)

    def item_operation(self, op, item, price, quantity, note = ""):
      price = abs(price)
      quantity = abs(quantity)
      if op == "sell":
        price = -price
        quantity = -quantity
        # pay tax
        self.operations = self.operations.append({
          "buy_or_sell": op,
          "item_name": "tax",
          "item_url": "tax",
          "item_id": "tax",
          "sell_confirmed": True,
          "item_price": ceil(int(payload["price"])*0.02),
          "item_note": f"tax for selling {-quantity} {item["name"]} for {-price}k {note}",
          "quantity": 1,
        }, ignore_index=True)
      pricePerUnit = price / float(quantity)
      self.operations = self.operations.append({
        "buy_or_sell": op,
        "item_name": item["name"],
        "item_url": item["url"],
        "item_id": item["id"],
        "sell_confirmed": False,
        "item_price": pricePerUnit,
        "item_note": note,
        "quantity": quantity,
      }, ignore_index=True)
      if len(self.inventory[self.inventory.item_id==item["id"]]) == 1:
        self.inventory.loc[self.inventory.item_id==item["id"], "quantity"] += quantity
        self.inventory.loc[self.inventory.item_id==item["id"], "item_price"] = pricePerUnit
      else:
        self.inventory = self.inventory.append({
          "item_name": item["name"],
          "item_url": item["url"],
          "item_id": item["id"],
          "quantity": quantity,
          "item_price": pricePerUnit,
        }, ignore_index=True)

if __name__ == "__main__":
  p = Persistance()
  print(p.inventory.tail())
