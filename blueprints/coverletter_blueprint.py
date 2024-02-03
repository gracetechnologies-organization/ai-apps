from flask import Blueprint, request, jsonify, current_app
import openai
from helpers.openaiHelper import get_openai_key_from_db
from middlewares.resauthorization import authorization_required

letter_blueprint = Blueprint("letter_blueprint", __name__)

openai.api_key = None

class InvalidResponseError(Exception):
    def __init__(self, message="Invalid response from AI. Unable to parse as text."):
        self.message = message
        super().__init__(self.message)

def get_completion(prompt, model="gpt-3.5-turbo-instruct", api_key=None):
    try:
        if api_key:
            openai.api_key = api_key
        else :
            raise ValueError("No API Key provided")

        response = openai.Completion.create(
            engine=model,
            prompt=prompt,
            max_tokens=800,
            n=1,
            stop=None,
            temperature=0
        )
        cover_letter_body = response.choices[0].text.strip()
        return cover_letter_body
    except (openai.error.OpenAIError, ValueError) as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        raise
    except Exception as e:
        current_app.logger.error(f"Error in get_completion function: {str(e)}")
        raise

@letter_blueprint.route('/api/ai/generate_letter', methods=['POST'])
@authorization_required
def generate_letter():
    try:
        
        api_key = get_openai_key_from_db()
        Uname = request.form.get('UserName')
        Cname = request.form.get('CompanyName')
        job_description = request.form.get('JobDescription')

        if Uname is None or job_description is None or Cname is None:
            return jsonify({"message": "Missing 'User Name', 'Company Name', or 'Job Description' in request data"}), 422
        
        elif len(job_description) < 10 or not job_description[:1].isalpha() or any(char in job_description for char in set('[~!@$%^&*()_{};\]$')):
            raise ValueError("Please try with correct and detailed job description.")

        prompt = f"""Generate a concise 90-word cover letter tailored for the [Company Name] job application. Highlight the candidate's qualifications, skills, and enthusiasm, based on the provided job description.
                    Company name: {Cname}
                    Job Description: {job_description}
                    Writer's name: {Uname}
                    """

        cover_letter_body = get_completion(prompt, api_key=api_key)

        return jsonify({"cover_letter_body": cover_letter_body}), 200
    except ValueError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": str(e)}), 500
    except InvalidResponseError as e:
        current_app.logger.error(f"Error occurred: {str(e)}")
        return jsonify({"message": "Try Again Later"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in generate_letter function: {str(e)}")
        return jsonify({"message": "Try Again Later"}), 500
