from flask import request, jsonify, Blueprint, current_app
import random, json, os, csv,ast
import boto3, botocore
import pandas as pd
from middlewares.resauthorization import authorization_required
from helpers.AWSHelper import get_Creds

iosresume_blueprint = Blueprint('iosresume', __name__)

Creds = get_Creds()

bedrock_runtime = boto3.client(
service_name = Creds["SERVICE_NAME"],
region_name = Creds["REGION_NAME"],
aws_access_key_id=Creds["AWS_ACCESS_KEY"],
aws_secret_access_key=Creds["AWS_SECRET_KEY"]
)

DATASETS_DIR = 'Datasets'
CSV_FILE = 'IOSDataset.csv'
CSV_PATH = os.path.join(DATASETS_DIR, CSV_FILE)

def save_to_csv(data):

    if not os.path.exists(DATASETS_DIR):
        os.makedirs(DATASETS_DIR)

    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='') as csvfile:
            fieldnames = ['JobDescription', 'Response']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    with open(CSV_PATH, 'a', newline='') as csvfile:
        fieldnames = ['JobDescription', 'Response']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(data)

def clean_response(txt):
    start_index = txt.find("{")
    end_index = txt.rfind("}") + 1
    json_data = txt[start_index:end_index]
    parsed_json = json.loads(json_data)
    return parsed_json

def random_response():
    df = pd.read_csv('Datasets/IOSDataset.csv')
    if 'Response' in df.columns:
        random_response = random.choice(df['Response'])
        response_dict = ast.literal_eval(random_response)
        json_response = json.loads(response_dict)
        return(json_response)
    else:
        current_app.logger.error("The 'Response' column does not exist in the DataFrame.")
        raise

def get_completion(prompt):
    body = json.dumps({"prompt":prompt, "max_tokens_to_sample": 800})
    modelId = "anthropic.claude-instant-v1"
    accept = "application/json"
    contentType = "application/json"

    try:

        response = bedrock_runtime.invoke_model(
            body=body, modelId=modelId, accept=accept, contentType=contentType
        )
        response_body = json.loads(response.get("body").read())
        return(clean_response(response_body.get("completion")))

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            current_app.logger.error(f"\x1b[41m{e.response['Error']['Message']}\
                    \nTo troubeshoot this issue please refer to the following resources.\
                    \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
                    \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n")
        else:
            raise
@iosresume_blueprint.route('/api/ai/generate_iosresume', methods=['POST'])
@authorization_required
def generate_resume():
    try:
                
        job_description = request.form.get('JobDescription')
        
        if job_description is None:
            return jsonify({"message" : "Job Description is missing."}), 422
        elif len(job_description) < 10 or not job_description[:1].isalpha() or any(char in job_description for char in set('[~!@$%^&*()_{};\]$')):
            return jsonify({"message" :"Please try with correct and detailed job description having no special characters."}), 422
        
        
        prompt = f"""Human: Generate resume data for a candidate based on the provided job description. Include the following sections:
                    Profession
                    Objective (250-270 characters only)
                    Experience (List of 2 JSON objects with Designation, Organization, JoiningDate, EndDate, and short 2 line JobDescription of max 100 characters only)
                    Qualification (List of 2 JSON objects with Degree, EducationalOrganization, Score in format (CGPA: ???/4.0), CompletionDate)
                    Achievements (List of 4 JSON objects having "AchievementTitle" key with with short achievement )
                    Projects (List of 4  JSON objects having only "ProjectTitle" key with short project title)
                    Skills (List of 4 JSON objects having only "SkillName" key)
                    Interests (List of 3 JSON object having only "Interest" key)
                    Ensure that the all keys must be same as defined section names (starting capital letter) and format of resume data must as JSON.
                    Job Description: "{job_description}"
                    Assistant:
                    """
        parsed_dict = get_completion(prompt)

        if parsed_dict is None:
            parsed_dict = random_response()
            return jsonify(parsed_dict), 200
        else:
            data = {'JobDescription': job_description, 'Response': parsed_dict}
            save_to_csv(data)
            return jsonify(parsed_dict), 200
    
    except ValueError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 422
    
    except Exception as e:
        current_app.logger.error(f"Error in generate_resume function: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500