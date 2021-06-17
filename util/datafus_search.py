import logging
import json
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
class CATEGORIES:
  weapons="weapons"
  equipments="equipments"
  consumables="consumables"
  resources="resources"

loaded = None

def openJSONdb():
    global loaded
    if not loaded:
        with open(resource_path("data/dofus.fr.json")) as db:
            loaded = json.load(db)
    return loaded

def get_category(cat):
  return openJSONdb()[cat]

def get_all_items():
  return get_category(CATEGORIES.weapons) + get_category(CATEGORIES.equipments) +\
     get_category(CATEGORIES.consumables) + get_category(CATEGORIES.resources)

def get_by_url(item_url):
  item = list(filter(lambda item: item["url"] == item_url, get_all_items()))
  if len(item) != 1:
    raise "found no or more than 1 item with this url [" + item_url + "] : " + str(item)
  return item[0]

def get_by_id(id):
  item = list(filter(lambda item: str(item["id"]) == str(int(id)), get_all_items()))
  if len(item) != 1:
    raise "found no or more than 1 item with this id [" + str(id) + "] : " + str(item)
  return item[0]

def get_craft(item_url):
  item = get_by_url(item_url)
  recipe = item["craft"]
  return recipe


def get_searchables():
  return list(sorted(map(lambda item: {
    "name":item["name"],
    "id": item["id"],
    "level": item["level"],
    "type": item["type"],
  }, get_all_items()),
     key=lambda item: item["name"]))

def get_ingredients(item):
  res = []
  logging.info(f"making ingredients list for {item['name']}")
  for ing in item["craft"]:
    logging.debug(ing)
    res.append({
      'item': get_by_url(ing["url"]),
      'quantity': ing["quantity"],
    })
  return res

if __name__ == "__main__":
  print(openJSONdb().keys())
  print(get_category(CATEGORIES.resources)[0])
  print(get_all_items()[0])
  print(get_craft(get_category(CATEGORIES.weapons)[0]["url"]))



