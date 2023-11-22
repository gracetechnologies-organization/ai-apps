# authorization.py
import logging
from flask import request, jsonify, current_app
from helpers.pdfHelper import validate_auth_token

logger = logging.getLogger(__name__)

def authorization_required(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            current_app.logger.warning("Token is missing")
            return jsonify({'message': 'Token is missing'}), 401

        if not validate_auth_token(token):
            current_app.logger.warning(f"Unauthorized token: {token}")
            return jsonify({'message': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated_function
