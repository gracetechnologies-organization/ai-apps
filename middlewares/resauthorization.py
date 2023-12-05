from flask import request, abort, current_app, jsonify
from helpers.resHelper import is_valid_token

def authorization_required(func):
    def wrapper(*args, **kwargs):
        auth_token = request.headers.get("Authorization")

        if not auth_token:
            current_app.logger.warning("Authorization token is missing")
            response = jsonify(message="Authorization token is missing")
            response.status_code = 401
            return response

        if not is_valid_token(auth_token):
            current_app.logger.warning("Unauthorized access with token: %s", auth_token)
            response = jsonify(message="Unauthorized Token")
            response.status_code = 401
            return response

        return func(*args, **kwargs)

    return wrapper
