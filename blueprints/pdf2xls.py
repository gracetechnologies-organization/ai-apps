import os
import tabula
import pandas as pd
from flask import Blueprint, request, send_file, current_app, jsonify, make_response
from io import BytesIO
from middlewares.pdfauthorization import authorization_required

pdf2xls_blueprint = Blueprint('pdf2xls_blueprint', __name__)

@pdf2xls_blueprint.route('/pdf2xls', methods=['POST'])
@authorization_required
def convert_pdf_to_xlsx():
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
        cwd = os.getcwd()
        uploads_dir = os.path.join(cwd, 'XLSPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == 'pdf':
            pdf_file_path = os.path.join(uploads_dir, filename)
            excel_file_path = os.path.join(uploads_dir, f"{filename.split('.')[0]}.xlsx")
            file.save(pdf_file_path)

            # Read PDF file
            tables = tabula.read_pdf(pdf_file_path, pages='all')

            # Write each table to a separate sheet in the Excel file
            with pd.ExcelWriter(excel_file_path) as writer:
                for i, table in enumerate(tables):
                    table.to_excel(writer, sheet_name=f'Sheet{i + 1}')

            os.remove(pdf_file_path)  # Delete the input PDF file

            # Sending the output file as a variable
            with open(excel_file_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Deleting the output Excel file
            os.remove(excel_file_path)

            response = make_response(send_file(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f"{filename.split('.')[0]}.xlsx"))
            return response, 200
        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .pdf file.")
            return jsonify({"error": "Invalid file format. Please upload a .pdf file."}), 422

    except Exception as e:
        current_app.logger.error(f"Error in /pdf2xlsx: {str(e)}")

        # Remove the files in case of an error
        if 'pdf_file_path' in locals() and os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)

        if 'excel_file_path' in locals() and os.path.exists(excel_file_path):
            os.remove(excel_file_path)

        return jsonify({'error': f"Try Again, This pdf cannot be converted"}), 500