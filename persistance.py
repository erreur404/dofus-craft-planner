import time
import logging
import uuid
import pandas as pd
from math import ceil
from os.path import exists


DB_FILE = "dofus-craft-planner-save.xlsx"
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
                "op_id",
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
                "item_id",
                "quantity",
                "crafted",
                "last_changed",
            ])

    def save(self):
        writer = pd.ExcelWriter(DB_FILE, engine="xlsxwriter")
        logging.debug(f"saving Persistance.operations to {DB_FILE}::sheet={OPERATIONS_SHEET}")
        logging.debug(self.operations)
        self.operations.to_excel(writer, sheet_name=OPERATIONS_SHEET, index=False)
        logging.debug(f"saving Persistance.inventory to {DB_FILE}::sheet={INVENTORY_SHEET}")
        logging.debug(self.inventory)
        self.inventory.to_excel(writer, sheet_name=INVENTORY_SHEET, index=False)
        logging.debug(f"saving Persistance.crafts to {DB_FILE}::sheet={CRAFT_SHEET}")
        self.crafts.to_excel(writer, sheet_name=CRAFT_SHEET, index=False)
        writer.save()

    def craft_add(self, item, quantity):
        self.crafts = self.crafts.append({
            "item_name": item["name"],
            "item_url": item["url"],
            "item_id": item["id"],
            "quantity": int(quantity),
            "crafted": 0,
        }, ignore_index=True)

    def craft_df_of(self, item, quantity, crafted):
        df = pd.DataFrame(columns=[
                "item_name",
                "item_url",
                "item_id",
                "quantity",
                "crafted",
                "last_changed",
        ])
        df = df.append({
            "item_name": item["name"],
            "item_url": item["url"],
            "item_id": item["id"],
            "quantity": quantity,
            "crafted": crafted,
            "last_changed": time.time(),
        }, ignore_index=True)
        return df
    
    def craft_one(self, item, ingredients):
        self.crafts.loc[self.crafts.item_id==item["id"], "crafted"] += 1
        self.add_quantity(item, 1)
        logging.debug("decrementing ingredients to craft one " + item["name"])
        logging.debug(ingredients)
        for ing in ingredients:
            self.add_quantity(ing["item"], -int(ing["needed"]))

    def craft_delete(self, item):
        self.crafts = self.crafts[self.crafts.item_id != item["id"]]

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
                "buy_or_sell": "buy",
                "item_name": "tax",
                "item_url": "tax",
                "item_id": "tax",
                "sell_confirmed": True,
                "item_price": ceil(abs(int(price))*0.02),
                "item_note": f"tax for selling { -quantity } { item['name'] } for { -price }k. " + note if note is not None else "",
                "quantity": 1,
                "op_id": str(uuid.uuid4()),
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
            "op_id": str(uuid.uuid4()),
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

    def inventory_initialize_item(self, item):
        if len(self.inventory[self.inventory.item_id==item["id"]]) == 0:
            self.inventory = self.inventory.append({
                "item_name": item["name"],
                "item_url": item["url"],
                "item_id": item["id"],
                "quantity": 0,
                "item_price": 0,
                "last_changed": time.time(),
            }, ignore_index=True)

    def set_quantity(self, item, quantity: int):
        id = item["id"]
        self.inventory_initialize_item(item)        
        self.inventory.loc[self.inventory.item_id == id, "quantity"] = quantity
        self.inventory.loc[self.inventory.item_id==item["id"], "last_changed"] = time.time()

    def get_quantity(self, id: str) -> int:
        res = list(self.inventory.loc[self.inventory.item_id == id]["quantity"])
        return 0 if len(res) == 0 else res[0]

    def set_price(self, item, price: int):
        if len(self.inventory[self.inventory.item_id==item["id"]]) == 1:
            self.inventory.loc[self.inventory.item_id==item["id"], "item_price"] = price
            self.inventory.loc[self.inventory.item_id==item["id"], "last_changed"] = time.time()
        else:
            self.inventory = self.inventory.append({
                "item_name": item["name"],
                "item_url": item["url"],
                "item_id": item["id"],
                "quantity": 0,
                "item_price": price,
                "last_changed": time.time(),
            }, ignore_index=True)

    def get_price(self, id: str) -> int:
        res = list(self.inventory.loc[self.inventory.item_id == id]["item_price"])
        return 0 if len(res) == 0 else res[0]

    def add_quantity(self, item, quantity: int):
        logging.info(f"adding {quantity} of {item['name']} to the inventory")
        id = item["id"]
        self.inventory_initialize_item(item)
        self.inventory.loc[self.inventory.item_id == id, "quantity"] += quantity


if __name__ == "__main__":
  p = Persistance()
  print(p.inventory.tail())
