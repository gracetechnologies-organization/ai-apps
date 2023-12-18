from flask import request, jsonify, Blueprint, current_app
import random, json, os, threading, csv,ast
import boto3, botocore
import pandas as pd
from helpers.genaiHelper import get_genai_key_from_db
from middlewares.SDauthorization import authorization_required
from helpers.AWSHelper import get_Creds

geniosresume_blueprint = Blueprint('geniosresume', __name__)

Creds = get_Creds()

bedrock_runtime = boto3.client(
service_name = Creds["SERVICE_NAME"],
region_name = Creds["REGION_NAME"],
aws_access_key_id=Creds["AWS_ACCESS_KEY"],
aws_secret_access_key=Creds["AWS_SECRET_KEY"]
)

data_list = []
data_lock = threading.Lock()

DATASETS_DIR = 'Datasets'
CSV_FILE = 'IOSDataset.csv'
CSV_PATH = os.path.join(DATASETS_DIR, CSV_FILE)

def save_to_csv(data):
    # Check if the directory exists, if not, create it
    if not os.path.exists(DATASETS_DIR):
        os.makedirs(DATASETS_DIR)

    # Check if the CSV file exists, if not, create it and write the header
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='') as csvfile:
            fieldnames = ['JobDescription', 'Response']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    # Append data to the CSV file
    with open(CSV_PATH, 'a', newline='') as csvfile:
        fieldnames = ['JobDescription', 'Response']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(data)

def clean_response(txt):
    start_index = txt.find("{")
    end_index = txt.rfind("}") + 1
    json_data = txt[start_index:end_index]
    parsed_json = json.loads(json_data)
    # formatted_json = json.dumps(parsed_json, indent=2)
    return parsed_json
    # required_section = json.dumps(parsed_dict, indent=2)
    # return required_section

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
    # try:
    #     if api_key:
    #         genai.configure(api_key= api_key)
    #     else:
    #         current_app.logger.error("No API key provided.")
    #         return jsonify({"message":"Please Try Again Later"})
    #     defaults = {
    #         'model': 'models/text-bison-001',
    #         'temperature': 0.1,
    #         'candidate_count': 1,
    #         'max_output_tokens': 800,
    #         'stop_sequences': [],
    #         'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":"BLOCK_LOW_AND_ABOVE"},{"category":"HARM_CATEGORY_TOXICITY","threshold":"BLOCK_LOW_AND_ABOVE"},{"category":"HARM_CATEGORY_VIOLENCE","threshold":"BLOCK_MEDIUM_AND_ABOVE"},{"category":"HARM_CATEGORY_SEXUAL","threshold":"BLOCK_MEDIUM_AND_ABOVE"},{"category":"HARM_CATEGORY_MEDICAL","threshold":"BLOCK_MEDIUM_AND_ABOVE"},{"category":"HARM_CATEGORY_DANGEROUS","threshold":"BLOCK_MEDIUM_AND_ABOVE"}],
    #         }
    #     response = genai.generate_text(
    #         **defaults,
    #         prompt=prompt
    #         )
    #     generated_text = response.result
    #     generated_text = clean_response(generated_text)
    #     return generated_text

    # except Exception as e:
    #     current_app.logger.error(f"Error in get_completion function: {str(e)}")
    #     raise

# Define a POST endpoint for your API
@geniosresume_blueprint.route('/api/ai/generate_geniosresume', methods=['POST'])
@authorization_required
def generate_resume():
    try:
            
        api_key = get_genai_key_from_db()
        
        job_description = request.form.get('JobDescription')
        
        if job_description is None:
            return jsonify({"message" : "Job Description is missing."}), 422
        elif len(job_description) < 10 or not job_description[:1].isalpha() or any(char in job_description for char in set('[~!@#$%^&*()_+{}":;\]+$')):
            return jsonify({"message" :"Please try with correct and detailed job description having no special characters."})
        
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
        # parsed_dict = get_completion(prompt, api_key)
        parsed_dict = get_completion(prompt)

        if parsed_dict is None:
            parsed_dict = random_response()
            return jsonify(parsed_dict), 200
        else:
            data = {'JobDescription': job_description, 'Response': parsed_dict}
            with data_lock:
                data_list.append(data)
            threading.Thread(target=save_to_csv, args=(data,)).start()
            return jsonify(parsed_dict), 200
    
    except ValueError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 422
    
    except Exception as e:
        current_app.logger.error(f"Error in generate_resume function: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
    