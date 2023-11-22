import pymongo

mongo_uri = "mongodb://localhost:27017/"
database_name = "AiDtabase"
collection_name = "pdf_coll"

def get_auth_token_from_db():
    try:
        client = pymongo.MongoClient(mongo_uri)
        database = client[database_name]
        collection = database[collection_name]

        document = collection.find_one({}, {"auth_token": 1, "_id": 0})
        
        if document:
            return document.get("auth_token")

    except Exception as e:
        print(f"An error occurred while retrieving auth token: {e}")

    finally:
        client.close()

    return None

def validate_auth_token(token):
    stored_token = get_auth_token_from_db()
    
    if stored_token and token == stored_token:
        return True

    return False
