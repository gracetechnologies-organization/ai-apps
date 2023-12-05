from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client ["AiDatabase"]
collection = db["SD_Coll"]