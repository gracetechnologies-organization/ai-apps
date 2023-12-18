from flask import Blueprint, request, jsonify, current_app
import openai, json, os, threading, csv
from helpers.openaiHelper import get_openai_key_from_db
from middlewares.resauthorization import authorization_required

andresume_blueprint = Blueprint("andresume_blueprint", __name__)

data_list = []
data_lock = threading.Lock()

DATASETS_DIR = 'Datasets'
CSV_FILE = 'AndroidDataset.csv'
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

openai.api_key = None

class InvalidResponseError(Exception):
    def __init__(self, message="Invalid response from AI. Unable to parse as JSON."):
        self.message = message
        super().__init__(self.message)

def get_completion(prompt, model="gpt-3.5-turbo-instruct", api_key=None):
    try:
        if api_key:
            openai.api_key = api_key
        else:
            raise ValueError("No API key provided")

        response = openai.Completion.create(
            engine=model,
            prompt=prompt,
            max_tokens=800,
            n=1,
            stop=None,
            temperature=0
        )

        generated_text = response.choices[0].text
        parsed_dict = json.loads(generated_text)
        return parsed_dict
    except (openai.error.OpenAIError, json.JSONDecodeError, ValueError) as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        raise
    except Exception as e:
        current_app.logger.error(f"Error in get_completion function: {str(e)}")
        raise

@andresume_blueprint.route('/api/ai/generate_andresume', methods=['POST'])
@authorization_required
def generate_resume():
    try:
        api_key = get_openai_key_from_db()
        name = request.form.get('Name')
        job_description = request.form.get('JobDescription')
        # user_api_key = request.form.get('ApiKey')

        if name is None or job_description is None or job_description.strip() == "" or name.strip() == "":
            return jsonify({"message": "Missing 'Name' or 'JobDescription' in request data"}), 422
        
        elif len(job_description) < 10 or not job_description[:1].isalpha() or any(char in job_description for char in set('[~!@#$%^&*()_+{}":;\]+$')):
            raise ValueError("Please try with correct and detailed job description having no special characters.")

        prompt = f"""Create a comprehensive CV for a candidate with a strong focus on their professional qualifications and experiences, tailored to the given job description. Data format must be (dd-mm-yyy). The CV must and only have following sections.

                    CV Sections:
                    - Job Title (Heading)
                    - Professional Summary (Up to 50 words)
                    - Employment History (List of 2 job titles, employers, start and end dates, cities, and short one line descriptions of experiences in each role)
                    - Education (List of 2 university names, degree titles, CGPA, start and completion dates)
                    - Skills (List 5 relevant skills)
                    - Interests (List 4 hobbies or interests i.e short names of max 10 characters only)

                    Format the CV as a JSON object with lowercase keys and underscores instead of spaces.

                    Details for CV Generation:
                    Name : "{name}"
                    Job Description: "{job_description}"
                    """

        parsed_dict = get_completion(prompt, api_key=api_key)
        data = {'JobDescription': job_description, 'Response': parsed_dict}

        with data_lock:
            data_list.append(data)

        threading.Thread(target=save_to_csv, args=(data,)).start()
        
        return jsonify(parsed_dict), 200
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error occurred: Response isn't in JSON format due to the job description provided: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
    
    except ValueError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": str(e)}), 500
    
    except InvalidResponseError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_resume function: {str(e)}")
        return jsonify({"message": "Try again with a detailed and correct job description."}), 500
