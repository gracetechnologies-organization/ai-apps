import os
import subprocess
import uuid
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from middlewares.pdfauthorization import authorization_required

ppt2pdf_blueprint = Blueprint('ppt2pdf_blueprint', __name__)

def convert_ppt_to_pdf_task(file, uploads_dir, ppt_path):
    try:
        file.save(ppt_path)
        subprocess.call(['soffice',
                         '--headless',
                         '--convert-to',
                         'pdf',
                         '--outdir',
                         uploads_dir,
                         ppt_path])


        pdf_filename = os.path.splitext(os.path.basename(ppt_path))[0] + ".pdf"
        pdf_path = os.path.join(uploads_dir, pdf_filename)
        with open(pdf_path, 'rb') as f:
            file_data = BytesIO(f.read())
        return pdf_filename, pdf_path, file_data

    finally:
        if os.path.exists(ppt_path):
            os.remove(ppt_path)

@ppt2pdf_blueprint.route('/ppt2pdf', methods=['POST'])
def convert_ppt_to_pdf():
    ppt_path = None
    pdf_path_for_deletion = None

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

        if file_ext in ['.ppt', '.pptx']:
            uuid_str = str(uuid.uuid4())[:8]
            ppt_filename = f"{filename}_{uuid_str}.pptx"
            ppt_path = os.path.join(uploads_dir, ppt_filename)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(convert_ppt_to_pdf_task, file, uploads_dir, ppt_path)
                pdf_filename, pdf_path, file_data = future.result()
            pdf_path_for_deletion = pdf_path

            response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True,
                                               download_name=pdf_filename))
            if pdf_path_for_deletion and os.path.exists(pdf_path_for_deletion):
                os.remove(pdf_path_for_deletion)

            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .ppt or .pptx file.")
            return jsonify({"error": "Invalid file format. Please upload a .ppt or .pptx file."}), 422
    except Exception as e:
        current_app.logger.error(f"Error in /ppt2pdf: {str(e)}")
        if ppt_path and os.path.exists(ppt_path):
            os.remove(ppt_path)
        if pdf_path_for_deletion and os.path.exists(pdf_path_for_deletion):
            os.remove(pdf_path_for_deletion)
        return jsonify({'error': f"Try Again"}), 500
