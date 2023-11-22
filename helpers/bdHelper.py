from config import client

def connect_to_auth_collection():
    db = client["AiDatabase"]
    auth_coll = db["auth-coll"]
    return auth_coll

def is_valid_token(auth_token):
    auth_coll = connect_to_auth_collection()

    # Check if the token exists in the database
    token_exists = auth_coll.find_one({"auth_token": auth_token}) is not None

    return token_exists
