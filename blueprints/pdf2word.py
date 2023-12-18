import os
import uuid
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from pdf2docx import parse
from io import BytesIO
from middlewares.pdfauthorization import authorization_required
from concurrent.futures import ThreadPoolExecutor

pdf2word_blueprint = Blueprint('pdf2word_blueprint', __name__)

@pdf2word_blueprint.route('/pdf2word', methods=['POST'])
@authorization_required
def convert_pdf_to_word():
    try:
        if 'file' not in request.files:
            current_app.logger.warning(f"No file part")
            return jsonify({"error": "No file part"})

        file = request.files['file']
        if file.filename == '':
            current_app.logger.warning(f"No selected file")
            return jsonify({"error": "No selected file"}), 422
        file_uuid = str(uuid.uuid4())
        filename, file_ext = os.path.splitext(file.filename)
        filename_with_uuid = f"{filename}_{file_uuid}{file_ext}"
        uploads_dir = os.path.join(os.getcwd(), 'DOCPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        file_path = os.path.join(uploads_dir, filename_with_uuid)
        file.save(file_path)

        if file_ext.lower() == '.pdf':
            converted_uuid = str(uuid.uuid4())
            word_filename = f"{filename}_{converted_uuid}.docx"
            word_path = os.path.join(uploads_dir, word_filename)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(parse, file_path, word_path, start=0, end=None)
                future.result()

            with open(word_path, 'rb') as f:
                file_data = BytesIO(f.read())

            os.remove(file_path)
            os.remove(word_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document', as_attachment=True, download_name=word_filename))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            os.remove(file_path)
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422

    except Exception as e:
        current_app.logger.error(f"Error in /pdf2word: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        if 'word_path' in locals() and os.path.exists(word_path):
            os.remove(word_path)
        return jsonify({'error': f"Try Again"}), 500
