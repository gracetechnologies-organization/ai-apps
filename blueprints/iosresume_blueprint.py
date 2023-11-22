from flask import request, jsonify, Blueprint, current_app
import openai, json, os, threading, csv
from helpers.openaiHelper import get_openai_key_from_db
from middlewares.bdauthorization import authorization_required

iosresume_blueprint = Blueprint('iosresume', __name__)

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

openai.api_key = None

def clean_and_parse_json(input_string):
    # Removing leading and trailing '\n' characters
    cleaned_string = input_string.strip()

    # Removing trailing commas from the string
    cleaned_string = cleaned_string.replace(",\n        }", "\n        }")

    try:
        # Converting the string to a JSON object
        parsed_dict = json.loads(cleaned_string)
        return parsed_dict
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        raise InvalidResponseError("Invalid JSON format. Unable to parse.")
class InvalidResponseError(Exception):
    def __init__(self, message="Invalid response from AI. Unable to parse as JSON."):
        self.message = message
        super().__init__(self.message)

def get_completion(prompt, model="gpt-3.5-turbo-instruct", api_key=None):
    try:
        if api_key:
            openai.api_key = api_key
        else:
            raise ValueError("No API key provided.")

        response = openai.Completion.create(
            engine=model,
            prompt=prompt,
            max_tokens=800,  # Adjust the desired length of the generated text
            n=1,  # Number of completions to generate
            stop=None,  # You can specify stop sequences to end the text
            temperature=0  # This is the degree of randomness of the model's output
        )
        generated_text = response.choices[0].text
        # parsed_dict = json.loads(generated_text)
        # return parsed_dict
        try:
            parsed_dict = json.loads(generated_text)
        except json.JSONDecodeError:
            parsed_dict = clean_and_parse_json(generated_text)

        return parsed_dict

    except (openai.error.OpenAIError, json.JSONDecodeError, ValueError) as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        raise
    except Exception as e:
        current_app.logger.error(f"Error in get_completion function: {str(e)}")
        raise

# Define a POST endpoint for your API
@iosresume_blueprint.route('/api/ai/generate_iosresume', methods=['POST'])
@authorization_required
def generate_resume():
    try:
            
        api_key = get_openai_key_from_db()
        
        job_description = request.form.get('JobDescription')
        # user_api_key = request.form.get('ApiKey')  # Extract user-provided API key
        
        if job_description is None:
            raise ValueError("Job Description is missing.")
        elif len(job_description) < 10 or not job_description[:1].isalpha() or any(char in job_description for char in set('[~!@#$%^&*()_+{}":;\]+$')):
            raise ValueError("Please try with correct and detailed job description having no special characters.")
        
        # Modify the prompt with the provided name and job_description
        prompt = f""" Generate resume data for a candidate based on the provided job description. Include the following sections:

                        Profession
                        Objective (250-270 characters only)
                        Experience (List of 2 JSON objects with Designation, Organization, JoiningDate, EndDate, and short one line JobDescription of max 100 characters only)
                        Qualification (List of 2 JSON objects with Degree, EducationalOrganization, Score in format (CGPA: ???/4.0), CompletionDate)
                        Achievements (List of 4 JSON objects having "AchievementTitle" key with value of max 10 characters)
                        Projects (List of 4  JSON objects having only "ProjectTitle" key)
                        Skills (List of 4 JSON objects having only "SkillName" key)
                        Interests (List of 3 JSON object having only "Interest" key)
                        Ensure that the format of resume data must as JSON.

                        Job Description: "{job_description}"
                        """

        # Generate the response using the OpenAI model, passing user_api_key if provided
        parsed_dict = get_completion(prompt, api_key=api_key)
        
        # Store data in a dictionary
        data = {'JobDescription': job_description, 'Response': parsed_dict}

        # Acquire lock before appending to the global list
        with data_lock:
            data_list.append(data)

        # Offload the file writing to a separate thread
        threading.Thread(target=save_to_csv, args=(data,)).start()

        # Return the response as JSON
        return jsonify(parsed_dict), 200
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error occurred:  response isn't in Json format because of job description provided: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
    
    except InvalidResponseError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
    
    except ValueError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": str(e)}), 422
    
    except Exception as e:
        current_app.logger.error(f"Error in generate_resume function: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500