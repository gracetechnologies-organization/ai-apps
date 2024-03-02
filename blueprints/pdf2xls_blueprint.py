import os
import tabula
import pandas as pd
from flask import Blueprint, request, send_file, current_app, jsonify, make_response
from io import BytesIO
import uuid
from concurrent.futures import ThreadPoolExecutor
from middlewares.pdfauthorization import authorization_required

pdf2xls_blueprint = Blueprint('pdf2xls_blueprint', __name__)

def convert_pdf_to_xlsx_task(file, uploads_dir, pdf_file_path):
    file.save(pdf_file_path)
    tables = tabula.read_pdf(pdf_file_path, pages='all')
    uuid_str = str(uuid.uuid4())[:8]
    excel_filename = f"{os.path.splitext(os.path.basename(pdf_file_path))[0]}_{uuid_str}.xlsx"
    excel_file_path = os.path.join(uploads_dir, excel_filename)
    with pd.ExcelWriter(excel_file_path) as writer:
        for i, table in enumerate(tables):
            table.to_excel(writer, sheet_name=f'Sheet{i + 1}')
    return excel_filename, excel_file_path

@pdf2xls_blueprint.route('/pdf2xls', methods=['POST'])
def convert_pdf_to_xlsx():
    pdf_file_path = None
    excel_file_path = None
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
        cwd = os.getcwd()
        uploads_dir = os.path.join(cwd, 'XLSPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == '.pdf':
            uuid_str = str(uuid.uuid4())[:8]
            pdf_filename = f"{filename}_{uuid_str}.pdf"
            pdf_file_path = os.path.join(uploads_dir, pdf_filename)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(convert_pdf_to_xlsx_task, file, uploads_dir, pdf_file_path)
                excel_filename, excel_file_path = future.result()
            if os.path.exists(pdf_file_path):
                os.remove(pdf_file_path)
            with open(excel_file_path, 'rb') as f:
                file_data = BytesIO(f.read())
            if os.path.exists(excel_file_path):
                os.remove(excel_file_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=excel_filename))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422

    except Exception as e:
        current_app.logger.error(f"Error in /pdf2xlsx: {str(e)}")
        if pdf_file_path and os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)
        if excel_file_path and os.path.exists(excel_file_path):
            os.remove(excel_file_path)
        return jsonify({'error': f"Try Again, This pdf cannot be converted"}), 500
