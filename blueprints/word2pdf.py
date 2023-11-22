import os
import subprocess
from flask import Blueprint, request, send_file, jsonify, current_app, make_response
from io import BytesIO
from middlewares.pdfauthorization import authorization_required

docx2pdf_blueprint = Blueprint('docx2pdf_blueprint', __name__)

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

        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Create the 'uploads' directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), 'DOCPDF')
        os.makedirs(uploads_dir, exist_ok=True)

        if file_ext == 'doc':
            doc_pdf_filename = filename.split('.')[0] + ".pdf"
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)

            # Convert DOC to PDF using LibreOffice
            subprocess.call(['libreoffice',
                             '--headless',  # Run LibreOffice in headless mode (no GUI)
                             '--convert-to',
                             'pdf',
                             '--outdir',
                             uploads_dir,
                             file_path])

            os.remove(file_path)  # Delete the input file

            # Sending the output file as a variable
            with open(os.path.join(uploads_dir, doc_pdf_filename), 'rb') as f:
                file_data = BytesIO(f.read())

            # Deleting the output PDF file
            os.remove(os.path.join(uploads_dir, doc_pdf_filename))

            response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True,
                                               download_name=f"{filename.split('.')[0]}.pdf"))
            return response, 200

        elif file_ext == 'docx':
            docx_filename = filename.split('.')[0] + ".docx"
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)

            # Convert DOCX to PDF using LibreOffice
            subprocess.call(['libreoffice',
                             '--convert-to',
                             'pdf',
                             '--outdir',
                             uploads_dir,
                             os.path.join(uploads_dir, docx_filename)])

            os.remove(file_path)  # Delete the input file

            # Sending the output file as a variable
            with open(os.path.join(uploads_dir, docx_filename.replace('.docx', '.pdf')), 'rb') as f:
                file_data = BytesIO(f.read())

            # Deleting the output PDF file
            os.remove(os.path.join(uploads_dir, docx_filename.replace('.docx', '.pdf')))

            response = make_response(send_file(file_data, mimetype='application/pdf', as_attachment=True,
                                               download_name=f"{filename.split('.')[0]}.pdf"))
            return response, 200

        else:
            current_app.logger.warning(f"Invalid file format. Please upload a .doc or .docx file.")
            return jsonify({"error": "Invalid file format. Please upload a .doc or .docx file."}), 422

    except Exception as e:
        current_app.logger.error(f"Error in /word2pdf: {str(e)}")

        # Deleting the uploaded file if an error occurs
        if 'file_path' in locals():
            if os.path.exists(file_path):
                os.remove(file_path)

        # Deleting the generated PDF file if it exists
        if 'doc_pdf_filename' in locals():
            if os.path.exists(os.path.join(uploads_dir, doc_pdf_filename)):
                os.remove(os.path.join(uploads_dir, doc_pdf_filename))

        return jsonify({'error': f"Try Again"}), 500
