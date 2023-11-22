import os
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from pdf2docx import parse
from io import BytesIO
from middlewares.pdfauthorization import authorization_required

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

        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Create the 'uploads' directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), 'DOCPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == 'pdf':
            pdf_path = os.path.join(uploads_dir, filename)
            file.save(pdf_path)
            word_filename = filename.split('.')[0] + ".docx"
            word_path = os.path.join(uploads_dir, word_filename)
            parse(pdf_path, word_path, start=0, end=None)
            os.remove(pdf_path)

            # Sending the output file as a variable
            with open(word_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Deleting the output Word file
            os.remove(word_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document', as_attachment=True, download_name=word_filename))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422
    except Exception as e:
        current_app.logger.error(f"Error in /pdf2word: {str(e)}")

        # Remove the files in case of an error
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)

        if 'word_path' in locals() and os.path.exists(word_path):
            os.remove(word_path)

        return jsonify({'error': f"Try Again"}), 500