from flask import Blueprint, request, jsonify, current_app
import os
from dbhelper import get_db_cursor  
import shutil

upload_blueprint = Blueprint("upload", __name__)

processed_images_folder = 'processed_images'
frame_images_path = 'uploads'
if not os.path.exists(frame_images_path):
    os.makedirs(frame_images_path)

@upload_blueprint.route('/upload', methods=['POST'])
def upload_image():
    try:
        connection, cursor = get_db_cursor()
        frame_x_start = request.form.get('frame_x_start')
        frame_x_end = request.form.get('frame_x_end')
        frame_y = request.form.get('frame_y')
        frame_text_color = request.form.get('frame_text_color') 
        gender = request.form.get('gender')
        uploaded_file = request.files['image']

        if all(val is not None for val in [frame_x_start, frame_x_end, frame_y, frame_text_color, gender]) and uploaded_file.filename != '':
            image_filename = uploaded_file.filename
            image_destination_path = os.path.join(frame_images_path, image_filename)
            uploaded_file.save(image_destination_path)

            insert_query = "INSERT INTO frame_data (frame_x_start, frame_x_end, frame_y, frame_text_color, gender, frame_image_path) VALUES (?, ?, ?, ?, ?, ?)"
            data = (frame_x_start, frame_x_end, frame_y, frame_text_color, gender, image_destination_path)  
            cursor.execute(insert_query, data)
            connection.commit()

            cursor.close()
            connection.close()

            return jsonify({"message": "Data inserted successfully"})

    except Exception as e:
        current_app.logger.error(f"Error in /upload: {str(e)}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Invalid input or file"}), 400

@upload_blueprint.route(f'/delete_mobile_id/<mobile_id>', methods=['DELETE'])
def delete_mobile_id(mobile_id):
    try:
        # User's directory Path
        user_directory = os.path.join(processed_images_folder, mobile_id)

        if os.path.exists(user_directory):
            # Delete the directory and its contents
            shutil.rmtree(user_directory)
            return jsonify({"message": f"Mobile ID '{mobile_id}' directory deleted successfully"})
        else:
            return jsonify({"message": f"Mobile ID '{mobile_id}' directory does not exist"})

    except Exception as e:
        current_app.logger.error(f"Error in /delete_mobile_id: {str(e)}")
        return jsonify({'error': str(e)}), 500