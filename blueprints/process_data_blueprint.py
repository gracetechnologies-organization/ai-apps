import os
import cv2
import openai
import tempfile
import time
import numpy as np
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from PIL import Image, ImageDraw, ImageFont
from dbhelper import get_db_cursor 
from helpers.openaiHelper import get_openai_key_from_db
from middlewares.bdauthorization import authorization_required
import re


processed_images_folder = 'processed_images'
if not os.path.exists(processed_images_folder):
    os.makedirs(processed_images_folder)

# Base URL for serving processed images
base_url = '/ai-birthday-frames-3/'

process_data_blueprint = Blueprint("process_data", __name__)

@process_data_blueprint.route('/process_data', methods=['POST'])
@authorization_required
def process_data():
    try:
        connection, cursor = get_db_cursor()

        api_key = get_openai_key_from_db()
                
        data = request.form  

        person_image = request.files['person_image']  
        frame_counter = int(data.get('frame_counter', 1))
        page = int(data.get('page', 1))
        global mobile_id
        mobile_id = data.get('mobile_id')
        # api_key = data.get('api_key') 
        gender = data.get('gender')
        openai.api_key = api_key
        generated_text = ""

        if frame_counter == 1 and page == 1:
            name = data.get('name')
            relation = data.get('relation')
            personality_traits = data.get('personality_traits')
            prompt = f"""
            Please give a maximum of 30 words sentence/paragraph in just english language to wish a birthday to my {relation}, gender is {gender}, and the is {name} and the {personality_traits} is this. So please give me a positive words to wish a happy birthday.
            give maximum 30 words sentence/paragraph. And the sentence/paragraph must be completed.
            """
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=100  
            )
            generated_text = response.choices[0].text.strip()
            generated_text = re.sub(r'"',"", generated_text)
            generated_text = re.sub(r'\n'," ", generated_text)

            if generated_text != "":
                pass
            else:
                generated_text = f"Wishing you a very Happy Birthday {name}. Enjoy your day."

        elif frame_counter > 1 or page > 1:
            generated_text = data.get('generated_text')
        else:
            return jsonify({'error': 'Some Error Occurred'}), 400

        if not person_image:
            return jsonify({'error': 'Person image not found in the request.'}), 400

        # Save the person image to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            person_image.save(temp_file.name)
            person_image_path = temp_file.name        

        # Generate processed images
        main_images = fetch_main_images_from_db(page, frame_counter, gender)

        processed_images = process_and_save_images(main_images, generated_text, person_image_path, mobile_id)

        # Clean up temporary image file
        os.remove(person_image_path)
        cursor.execute("SELECT * FROM frame_data WHERE gender = ?", (gender,))
        data1 = cursor.fetchall()

        base_image_url = request.base_url.rsplit('/', 1)[0] + base_url
        processed_images = [base_image_url + image_path for image_path in processed_images]
        # print("processed_images", processed_images)

        return jsonify({
            'generated_text': generated_text,
            'processed_images': processed_images,
            'total_frames_in_db': len(data1)
        })

    except Exception as e:
        current_app.logger.error(f"Error in /process_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Fetch the Birthday frames from the SQLite3 database
def fetch_main_images_from_db(page, frame_counter, gender):
    connection, cursor = get_db_cursor()
    cursor.execute(f"SELECT * FROM frame_data WHERE gender = ? LIMIT ? OFFSET ?;", (gender, frame_counter, (page - 1) * frame_counter))

    data = cursor.fetchall()
    print("data", data)
    main_images = []

    for item in data:
        frame_id, frame_x_start, frame_x_end, frame_y, frame_text_color, frame_image_path, gender = item
        image_path = os.path.join(current_app.root_path, frame_image_path).replace("\\", "/")
        print("frame_image_path", frame_image_path)
        frame_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

        if frame_image is not None:
            main_images.append((frame_image, frame_x_start, frame_x_end, frame_y, frame_text_color))
        else:
            current_app.logger.error(f'Error loading image: {image_path}')
    return main_images

# Process and save images
def process_and_save_images(main_images, generated_text, person_image_path, mobile_id):
    try:
        # Load the person image
        person_image = cv2.imread(person_image_path, cv2.IMREAD_UNCHANGED)

        # Directory to save the processed images
        user_directory = os.path.join(processed_images_folder, f"{mobile_id}").replace("\\", "/")
        os.makedirs(user_directory, exist_ok=True)
        processed_images = []

        for i, main_image_data in enumerate(main_images):
            main_image, x_start, x_end, y, frame_text_color = main_image_data
            result_image = process_main_image(main_image, x_start, x_end, y, frame_text_color, generated_text, person_image)
            
            if result_image is not None:
                current_time_milliseconds = int(time.time() * 1000)
                output_directory = os.path.join(user_directory, f'processed_image_{i + 1}_{current_time_milliseconds}.jpg').replace("\\", "/")
                cv2.imwrite(output_directory, result_image)
                processed_images.append(output_directory)
        
        return processed_images
    except Exception as e:
        current_app.logger.error(f"Error processing and saving images: {str(e)}")
        raise

# Map person image on the transparent portion of the birthday frame
def process_main_image(main_image, x_start, x_end, y, frame_text_color, generated_text, person_image):
    try:
        alpha_channel = main_image[:, :, 3]
        y_array, x_array = np.where(alpha_channel == 0)
        min_x, max_x = min(x_array), max(x_array)
        min_y, max_y = min(y_array), max(y_array)

        transparent_width = max_x - min_x
        transparent_height = max_y - min_y

        resized_person_image = cv2.resize(person_image, (transparent_width, transparent_height))
        main_image[min_y:max_y, min_x:max_x, :3] = resized_person_image
        main_image[min_y:max_y, min_x:max_x, 3] = 255

        new_text = generated_text
        words = new_text.split()
        font_color = eval(frame_text_color)
        fontpath = "fonts/Poppins-Medium.ttf"
        
        # Calculate available text width
        available_text_width = x_end - x_start

        # Initialize PIL image and draw object
        img_pil = Image.fromarray(main_image)
        draw = ImageDraw.Draw(img_pil)

        font_size = 17  
        line_height = 22  
        font = ImageFont.truetype(fontpath, font_size)

        lines = []
        current_line = []

        # Construct lines of text within the available width
        for word in words:
            test_line = ' '.join(current_line + [word]).strip()
            text_bbox = draw.textbbox((x_start, 0), test_line, font=font)
            text_width = text_bbox[2] - text_bbox[0]

            if text_width <= available_text_width:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]

        # Add the last line to the list
        if current_line:
            lines.append(current_line)

        # Calculate the text position and justify the text
        text_y = y
        for line in lines:
            line_text = ' '.join(line)
            text_bbox = draw.textbbox((x_start, 0), line_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]

            # Calculate the text position to justify it
            text_x = x_start + (available_text_width - text_width) // 2

            # Draw the justified line of text
            draw.text((text_x, text_y), line_text, font=font, fill=font_color)

            # Move to the next line
            text_y += line_height

        main_image = np.array(img_pil)

        return main_image
    except Exception as e:
        current_app.logger.error(f"Error processing main image: {str(e)}")
        return None

@process_data_blueprint.route(f'/{base_url}processed_images/<mobile_id>/<filename>')
def serve_image(mobile_id, filename):
    return send_from_directory(os.path.join(processed_images_folder, mobile_id), filename)