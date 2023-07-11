import cv2
import face_recognition
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import os
import requests
import json
from pymongo import MongoClient
import numpy as np
from datetime import datetime
import zipfile
import shutil
import platform


def getfile(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            process(file_path)
            print("File one completed")
    print("Completed processing all JSON files.")


def getpath():
    root = tk.Tk()
    root.withdraw()
    # Open file dialog to select an image file
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.json; *.webp;*.jpeg; *.png")])
    return file_path


#                                                     comapring
def compare(photos, path):
    import numpy as np
    for sublist in photos:
        array1 = np.array(sublist)
        image2 = face_recognition.load_image_file(path)
        image2_rgb = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
        try:
            encoding2 = face_recognition.face_encodings(image2_rgb)[0]
            results = face_recognition.compare_faces([array1], encoding2)
            if results[0]:
                print("The faces are a match.")
                return True

        except:
            pass
    # else:
    # print("The faces are not a match.")


def mongotopython():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['project']
    path = getpath()
    # Load documents from the 'user_info' collection
    photo_info = db['photos']
    documents = photo_info.find()
    # Iterate over the documents
    for document in documents:
        # Access the fields in each document
        user_id = document['user_id']
        photo_id = document['id_photo']
        photos = []
        for key in document.keys():
            if key.startswith('photo'):
                photos.append(document[key])
        flag = compare(photos, path)
        if flag:
            print("Completed")
            print(user_id)
            client.close()
            return True

    print("Completed")
    client.close()
    return False
    # Close the MongoDB connection
    


#                                                           json to db

def encoding_func(path):
    try:
        image1 = face_recognition.load_image_file(path)
        image1_rgb = cv2.cvtColor(image1, cv2.COLOR_BGR2RGB)

        face_encodings = face_recognition.face_encodings(image1_rgb)
        if len(face_encodings) > 0:
            if len(face_encodings) > 1:
                return face_encodings
            else:

                return face_encodings
        else:
            return None
    except:
        return None


def photo_download(url, id, j):
    response = requests.get(url)
    date = datetime.now().strftime("%Y-%m-%d")  # Get the current date
    id = id + "_photo_" + str(j)
    date = "Batch_" + date

    directory_path = f"images/{date}"
    os.makedirs(directory_path, exist_ok=True)  # Create the directory if it doesn't exist

    file_path = os.path.join(directory_path, f"{id}.webp")
    with open(file_path, 'wb') as f:
        f.write(response.content)

    return file_path, encoding_func(file_path)


def save_json_zip(json_file):
    date = datetime.now().strftime("%Y-%m-%d")  # Get the current date
    date = "Batch_" + date
    directory = f"images/{date}"
    os.makedirs(directory, exist_ok=True)  # Create the directory if it doesn't exist
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H-%M-%S")
    import uuid
    myuuid = uuid.uuid4()
    print('Your UUID is: ' + str(myuuid))
    zip_file_path = os.path.join(directory, formatted_datetime + str(myuuid) + "_json_files.zip")
    temp_zip_file_path = os.path.join(directory, "temp_json_files.zip")

    if os.path.exists(zip_file_path):
        with zipfile.ZipFile(zip_file_path, 'r') as original_zip:
            with zipfile.ZipFile(temp_zip_file_path, 'w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                for item in original_zip.infolist():
                    if item.filename != os.path.basename(json_file):
                        temp_zip.writestr(item, original_zip.read(item.filename))

                # Add the new JSON file to the temporary zip
                temp_zip.write(json_file, os.path.basename(json_file))

        # Replace the original zip file with the temporary one
        shutil.move(temp_zip_file_path, zip_file_path)
    else:
        with zipfile.ZipFile(zip_file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            # Add the JSON file to the zip
            zipf.write(json_file, os.path.basename(json_file))


def addphototodb(db, photo_info):
    photo_id = photo_info['id_photo']
    existing_photo = db.photos.find_one({'id_photo': photo_id})
    if existing_photo is None:
        db.photos.insert_one(photo_info)


# load the JSON data
def process(file_path):
    json_file_path = file_path

    client = MongoClient('mongodb://localhost:27017/')
    db = client['project']
    # Load the JSON data from the file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    # create a list to hold the filtered data
    processed_ids = []
    k = 0
    # iterate over the users in the results
    for result in data['data']['results']:
        if result['type'] == 'user':
            user = result['user']
            # interest=result['experiment_info']
            user_id = user['_id']
            if user_id in processed_ids:
                continue
            processed_ids.append(user_id)
            try:
                interests = [interest['name'] for interest in
                             result['experiment_info']['user_interests']['selected_interests']]
                interests = ', '.join(interests)
            except:
                pass
            try:
                schools = [schools['name'] for schools in user['schools']]
                schools = ', '.join(schools)
            except:
                pass
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            user_info = {
                'id': user['_id'],
                'badges': user['badges'],
                'bio': user['bio'],
                'birth_date': user['birth_date'],
                'name': user['name'],
                'gender': user['gender'],
                'jobs': user['jobs'],
                'schools': schools,
                'interests': interests,
                'Time': formatted_datetime
            }
            user_id = user_info['id']
            existing_user = db.user_info.find_one({'id': user_id})
            if existing_user is None:
                db.user_info.insert_one(user_info)
            # create a list to hold the photo info
            user_info['photos'] = []
            j = 1
            # iterate over the photos
            photo_info = {}
            for photo in user['photos']:
                # iterate over the processed files
                for processed_file in photo['processedFiles']:
                    # check the height and width
                    if processed_file['height'] == 800 and processed_file['width'] == 640:
                        # create a dictionary with the photo id and URL
                        file_p, hash1 = photo_download(processed_file['url'], photo['id'], j)
                        if hash1 is None:
                            photo_info = {
                                'user_id': user['_id'],
                                'id_photo': photo['id'],
                            }
                            continue
                        else:
                            if len(hash1) > 1:
                                for i in range(0, len(hash1)):
                                    encoding = hash1[i]
                                    photo_info = {
                                        'user_id': user['_id'],
                                        'id_photo': photo['id'],
                                        # 'url': processed_file['url']
                                        'photo ' + str(j) + " Face " + str(i + 1): encoding.tolist(),
                                        'path': file_p
                                    }
                                    photo_id = photo_info['id_photo']
                                    db.photos.insert_one(photo_info)

                                continue
                            else:
                                encoding = hash1[0]
                                photo_info = {
                                    'user_id': user['_id'],
                                    'id_photo': photo['id'],
                                    # 'url': processed_file['url']
                                    'photo ' + str(j): encoding.tolist(),
                                    'path': file_p
                                }

                        j = j + 1
                addphototodb(db, photo_info)

    save_json_zip(file_path)
    client.close()


print("Press 1 to choose a JSON file to load in MongoDB")
print("Press 2 to choose a directory to process all JSON files to load in MongoDB")
print("Press 3 to compare the faces")
print("Press 4 to exit")
while True:
    choice = int(input("Enter your choice: "))
    if choice == 1:
        process(getpath())
        print("completed")
    elif choice == 2:
        print("Enter the path of the directory")
        directory = input("Enter: ")
        getfile(directory)
    elif choice == 3:
        flag = mongotopython()
        if flag:
            print("True")
        else:
            print("False")
    elif choice == 4:
        break

