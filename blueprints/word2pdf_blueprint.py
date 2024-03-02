import os
import subprocess
import concurrent.futures
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from middlewares.pdfauthorization import authorization_required
import uuid

docx2pdf_blueprint = Blueprint('docx2pdf_blueprint', __name__)

def convert_and_cleanup(file_path, uploads_dir, filename):
    try:
        file_ext = filename.rsplit('.', 1)[1].lower()

        if file_ext == 'doc':
            doc_pdf_filename = filename.split('.')[0] + ".pdf"
            subprocess.call(['libreoffice',
                             '--headless',
                             '--convert-to',
                             'pdf',
                             '--outdir',
                             uploads_dir,
                             file_path])

        elif file_ext == 'docx':
            docx_filename = filename.split('.')[0] + ".docx"
            subprocess.call(['libreoffice',
                             '--convert-to',
                             'pdf',
                             '--outdir',
                             uploads_dir,
                             os.path.join(uploads_dir, docx_filename)])

        else:
            raise ValueError("Invalid file format. Please upload a .doc or .docx file.")
        output_filename = doc_pdf_filename if file_ext == 'doc' else docx_filename.replace('.docx', '.pdf')
        with open(os.path.join(uploads_dir, output_filename), 'rb') as f:
            file_data = BytesIO(f.read())

        return file_data, output_filename

    except Exception as e:
        current_app.logger.error(f"Error in converting {filename}: {str(e)}")
        raise

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        output_filepath = os.path.join(uploads_dir, doc_pdf_filename) if file_ext == 'doc' else os.path.join(uploads_dir, docx_filename.replace('.docx', '.pdf'))
        if os.path.exists(output_filepath):
            os.remove(output_filepath)

@docx2pdf_blueprint.route('/word2pdf', methods=['POST'])
@authorization_required
def convert_word_to_pdf():
    try:
        if 'file' not in request.files:
            current_app.logger.warning(f"No file part")
            return jsonify({"error": "No file part"}), 422

        file = request.files['file']
        if file.filename == '':
            current_app.logger.warning(f"No selected file")
            return jsonify({"error": "No selected file"}), 422

        filename, file_extension = os.path.splitext(file.filename)
        unique_filename = str(uuid.uuid4()) + file_extension
        uploads_dir = os.path.join(os.getcwd(), 'DOCPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        file_path = os.path.join(uploads_dir, unique_filename)
        file.save(file_path)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(convert_and_cleanup, file_path, uploads_dir, unique_filename)
            file_data, output_filename = future.result()

        response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True, download_name=output_filename))
        return response, 200

    except Exception as e:
        current_app.logger.error(f"Error in /word2pdf: {str(e)}")
        return jsonify({'error': f"Try Again"}), 500
