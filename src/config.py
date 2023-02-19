from pymongo import MongoClient
from json import load

mongo_client = MongoClient(host="localhost", port=27017)

with open("config.json") as f:
    json_data = load(f)

    TOKEN = json_data["BOT_TOKEN"]
    STRIKES_BEFORE_BAN = json_data["STRIKES_BEFORE_BAN"]