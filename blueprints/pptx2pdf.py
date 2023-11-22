import os
import subprocess
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from middlewares.pdfauthorization import authorization_required

ppt2pdf_blueprint = Blueprint('ppt2pdf_blueprint', __name__)

@ppt2pdf_blueprint.route('/ppt2pdf', methods=['POST'])
@authorization_required
def convert_ppt_to_pdf():
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

        if file_ext in ['ppt', 'pptx']:
            ppt_path = os.path.join(uploads_dir, filename)
            file.save(ppt_path)

            # Convert PPT/PPTX to PDF using LibreOffice
            subprocess.call(['soffice',
                             '--headless',  # Run LibreOffice in headless mode (no GUI)
                             '--convert-to',
                             'pdf',
                             '--outdir',
                             uploads_dir,
                             ppt_path])

            # Sending the output file as a variable
            pdf_filename = filename.split('.')[0] + ".pdf"
            pdf_path = os.path.join(uploads_dir, pdf_filename)

            with open(pdf_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Delete the uploaded .ppt or .pptx file
            os.remove(ppt_path)

            # Delete the converted .pdf file
            os.remove(pdf_path)

            response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True,
                                               download_name=f"{filename.split('.')[0]}.pdf"))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .ppt or .pptx file.")
            return jsonify({"error": "Invalid file format. Please upload a .ppt or .pptx file."}), 422
    except Exception as e:
        current_app.logger.error(f"Error in /ppt2pdf: {str(e)}")

        # Remove the files in case of an error
        if 'ppt_path' in locals() and os.path.exists(ppt_path):
            os.remove(ppt_path)

        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)

        return jsonify({'error': f"Try Again"}), 500
