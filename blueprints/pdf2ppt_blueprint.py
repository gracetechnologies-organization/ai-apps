import os
import subprocess
import uuid
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from middlewares.pdfauthorization import authorization_required

pdf2ppt_blueprint = Blueprint('pdf2ppt_blueprint', __name__)

def convert_pdf_to_ppt_task(file, uploads_dir, pdf_path):
    file.save(pdf_path)
    subprocess.call(['soffice',
                     '--infilter=impress_pdf_import',
                     '--convert-to',
                     'ppt',
                     '--outdir',
                     uploads_dir,
                     pdf_path])
    ppt_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".ppt"
    ppt_path = os.path.join(uploads_dir, ppt_filename)

    with open(ppt_path, 'rb') as f:
        file_data = BytesIO(f.read())

    return ppt_filename, ppt_path, file_data

@pdf2ppt_blueprint.route('/pdf2ppt', methods=['POST'])
def convert_pdf_to_ppt():
    pdf_path = None
    ppt_path = None
    try:
        if 'file' not in request.files:
            current_app.logger.warning(f"No file part")
            return jsonify({"error": "No file part"}), 422

        file = request.files['file']
        if file.filename == '':
            current_app.logger.warning(f"No selected file")
            return jsonify({"error": "No selected file"}), 422

        filename, file_ext = os.path.splitext(file.filename)
        file_ext = file_ext.lower()
        uploads_dir = os.path.join(os.getcwd(), 'PPTPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == '.pdf':
            uuid_str = str(uuid.uuid4())[:8]
            pdf_filename = f"{filename}_{uuid_str}.pdf"
            pdf_path = os.path.join(uploads_dir, pdf_filename)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(convert_pdf_to_ppt_task, file, uploads_dir, pdf_path)
                ppt_filename, ppt_path, file_data = future.result()
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.ms-powerpoint', as_attachment=True,
                                               download_name=ppt_filename))
            if os.path.exists(ppt_path):
                os.remove(ppt_path)

            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422
    
    except Exception as e:
        current_app.logger.error(f"Error in /pdf2ppt: {str(e)}")
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        if ppt_path and os.path.exists(ppt_path):
            os.remove(ppt_path)
        return jsonify({'error': f"Try Again"}), 500
