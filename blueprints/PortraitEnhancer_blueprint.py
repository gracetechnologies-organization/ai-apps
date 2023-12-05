from flask import Flask, request, jsonify, Blueprint, current_app
import boto3, botocore, requests, json
import time
from helpers.CredentialsHelper import get_Creds
from middlewares.SDauthorization import authorization_required

PE_blueprint = Blueprint('PE_blueprint', __name__)

Creds = get_Creds()

S3_BUCKET = Creds["S3_BUCKET"]
AWS_ACCESS_KEY = Creds["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = Creds["AWS_SECRET_KEY"]
DIFFUSION_KEY = Creds["DIFFUSION_KEY"]
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_s3(file):
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        file_name = file.filename
        s3.upload_fileobj(file, S3_BUCKET, file_name)
        presigned_url = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET, 'Key': file_name}, ExpiresIn=3600)
        return presigned_url
    except botocore.exceptions.ClientError as e:
        current_app.logger.error(f"S3 Upload Error: {str(e)}")
        raise e

def call_stable_diffusion_api(url):
    try:
        payload = json.dumps({
            "key": DIFFUSION_KEY,
            "url": url,
            "scale": 2,
            "webhook": None,
            "face_enhance": True
        })
        headers = {'Content-Type': 'application/json'}
        response = requests.post("https://stablediffusionapi.com/api/v3/super_resolution", headers=headers, data=payload, timeout=20)
        response_data = response.json()
        if response_data["status"] == "success":
            clean_url = response_data["output"].replace("\\", "")  
            return clean_url
        elif response_data["status"] == "processing":
            return handle_processing_status(response_data["fetch_result"])
        else:
            current_app.logger.info(response_data)
            current_app.logger.error(f"Stable Diffusion API Error: {response_data['status']}")
            raise Exception("Server is currently on its maximum performance. Please try again later.")
    except requests.Timeout:
        current_app.logger.info(f"SD API is taking more than 20 to respod")
        raise Exception("Server is currently on its maximum performance. Please try again later.")
    except Exception as e:
        current_app.logger.error(f"Stable Diffusion API Error: {str(e)}")
        raise Exception("Server is currently on its maximum performance. Please try again later with smaller image.")

def handle_processing_status(fetch_result_url):
    max_retries = 3
    retry_interval = 4
    max_timeout = 3

    for _ in range(max_retries):
        try:
            fetch_payload = json.dumps({
            "key": DIFFUSION_KEY,
            })
            headers = {'Content-Type': 'application/json'}
            response = requests.post(fetch_result_url, headers=headers, data=fetch_payload, timeout=max_timeout)
            response_data = response.json()

            if response_data["status"] == "success":
                clean_url = response_data["output"].replace("\\", "")
                return clean_url
            elif response_data["status"] == "processing":
                time.sleep(retry_interval)
            else:
                current_app.logger.info(response_data)
                current_app.logger.error(f"Fetch Result API Error: {response_data['status']}")
                raise Exception("Server is currently on its maximum performance. Please try again later.")
        except requests.Timeout:
            current_app.logger.info(f"SD API is taking more than 20 to respod")
            raise Exception("Server is currently on its maximum performance. Please try again later.")
        except Exception as e:
            current_app.logger.error(f"Fetch Result API Error: {str(e)}")
            raise Exception("Server is currently on its maximum performance. Please try again later.")
        
    current_app.logger.info("Fetch Result API Error: Maximum retries reached without success.")
    raise Exception("Server is currently on its maximum performance. Please try again later.")

@PE_blueprint.route('/PortraitEnhance', methods=['POST'])
@authorization_required
def PortraitEnhance():
    file = request.files.get('file')
    
    if not file:
        return jsonify({"error": "No file provided"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format. Only .png or .jpg files are allowed."}), 400

    try:
        presigned_url = upload_to_s3(file)
        clean_url = call_stable_diffusion_api(presigned_url)
        return jsonify({"output_url" : clean_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500