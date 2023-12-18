from flask import Blueprint, request, send_file, current_app
from rembg import remove
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from middlewares.SDauthorization import authorization_required

bgrem_blueprint = Blueprint('bgrem_blueprint', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(input_data):
    output_data = remove(input_data)
    return output_data

@bgrem_blueprint.route('/remove_background', methods=['POST'])
@authorization_required
def remove_background():
    if 'file' not in request.files:
        return {'error': 'No file part'}, 400

    file = request.files['file']

    if file.filename == '':
        return {'error': 'No selected file'}, 400
    
    if not allowed_file(file.filename):
        return {"error": "Invalid file format. Only .png or .jpg files are allowed."}, 400

    try:
        input_data = file.read()
        with ThreadPoolExecutor() as executor:
            output_data = executor.submit(process_image, input_data).result()
            
            return send_file(
                BytesIO(output_data),
                mimetype='image/png',
                download_name='output.png',
                as_attachment=True
            )

    except Exception as e:
        current_app.logger.error(f"error: {str(e)}")
        return {'error': 'Try Again later'}, 500

