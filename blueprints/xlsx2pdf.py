import os
import subprocess
import uuid
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from middlewares.pdfauthorization import authorization_required

xls2pdf_blueprint = Blueprint('xls2pdf_blueprint', __name__)

def convert_xls_to_pdf_task(file, uploads_dir, xls_path):
    file.save(xls_path)

    # Convert XLS or XLSX to PDF using LibreOffice
    subprocess.call(['libreoffice',
                     '--headless',  # Run LibreOffice in headless mode (no GUI)
                     '--convert-to',
                     'pdf:calc_pdf_Export',
                     '--outdir',
                     uploads_dir,
                     xls_path])

    # Sending the output file as a variable
    pdf_filename = os.path.splitext(os.path.basename(xls_path))[0] + ".pdf"
    pdf_path = os.path.join(uploads_dir, pdf_filename)

    with open(pdf_path, 'rb') as f:
        file_data = BytesIO(f.read())

    return pdf_filename, pdf_path, file_data

@xls2pdf_blueprint.route('/xls2pdf', methods=['POST'])
def convert_xls_to_pdf():
    xls_path = None
    pdf_path = None

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

        # Create the 'uploads' directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), 'XLSPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext in ['.xlsx', '.xls']:
            uuid_str = str(uuid.uuid4())[:8]
            xls_filename = f"{filename}_{uuid_str}.xlsx"
            xls_path = os.path.join(uploads_dir, xls_filename)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(convert_xls_to_pdf_task, file, uploads_dir, xls_path)
                pdf_filename, pdf_path, file_data = future.result()

            # Delete the uploaded .xls or .xlsx file with UUID
            if os.path.exists(xls_path):
                os.remove(xls_path)

            response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True,
                                               download_name=pdf_filename))

            # Delete the converted .pdf file with UUID
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .xls or .xlsx file.")
            return jsonify({"error": "Invalid file format. Please upload a .xls or .xlsx file."}), 422
    except Exception as e:
        current_app.logger.error(f"Error in /xls2pdf: {str(e)}")

        # Remove the files in case of an error
        if xls_path and os.path.exists(xls_path):
            os.remove(xls_path)

        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

        return jsonify({'error': f"Try Again"}), 500

