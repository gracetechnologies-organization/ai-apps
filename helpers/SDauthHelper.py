from config import collection, client

def get_SDauth_token_from_db():
    try:
        document = collection.find_one({}, {"auth_token": 1, "_id": 0})
        if document:
            return document.get("auth_token")
    except Exception as e:
        print(f"An error occurred while retrieving auth token: {e}")

    # finally:
    #     client.close()
    return None

def validate_auth_token(token):
    stored_token = get_SDauth_token_from_db()
    
    if stored_token and token == stored_token:
        return True
    return False
