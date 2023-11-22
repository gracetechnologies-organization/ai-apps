from config import client

def connect_to_openai_collection():
    db = client["AiDatabase"]
    openai_coll = db["openai_coll"]
    return openai_coll

def get_openai_key_from_db():
    openai_coll = connect_to_openai_collection()

    # Assuming there is only one document in openai_coll
    result = openai_coll.find_one({}, {"openai_key": 1, "_id": 0})

    if result and "openai_key" in result:
        return result["openai_key"]
    else:
        return None