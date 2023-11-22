import os
import subprocess
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from middlewares.pdfauthorization import authorization_required

pdf2ppt_blueprint = Blueprint('pdf2ppt_blueprint', __name__)

@pdf2ppt_blueprint.route('/pdf2ppt', methods=['POST'])
@authorization_required
def convert_pdf_to_ppt():
    try:
        if 'file' not in request.files:
            current_app.logger.warning(f"No file part")
            return jsonify({"error": "No file part"}), 422

        file = request.files['file']
        if file.filename == '':
            current_app.logger.warning(f"No selected file")
            return jsonify({"error": "No selected file"}), 422

        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Create the 'uploads' directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), 'PPTPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == 'pdf':
            pdf_path = os.path.join(uploads_dir, filename)
            file.save(pdf_path)

            # Convert PDF to PPT using LibreOffice
            subprocess.call(['soffice',
                             '--infilter=impress_pdf_import',
                             '--convert-to',
                             'ppt',
                             '--outdir',
                             uploads_dir,
                             pdf_path])

            # Sending the output file as a variable
            ppt_filename = filename.split('.')[0] + ".ppt"
            ppt_path = os.path.join(uploads_dir, ppt_filename)

            with open(ppt_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Delete the uploaded .pdf file
            os.remove(pdf_path)

            # Delete the converted .ppt file
            os.remove(ppt_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.ms-powerpoint', as_attachment=True,
                                               download_name=f"{filename.split('.')[0]}.ppt"))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422
    except Exception as e:
        current_app.logger.error(f"Error in /pdf2ppt: {str(e)}")

        # Remove the files in case of an error
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)

        if 'ppt_path' in locals() and os.path.exists(ppt_path):
            os.remove(ppt_path)

        return jsonify({'error': f"Try Again"}), 500
