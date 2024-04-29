import os
from datetime import *
from io import BytesIO
from traceback import print_exc

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from jsonschema import ValidationError, validate
from pymongo import MongoClient, server_api

# from base64 import b64encode,b64decode

# from pymongo.server_api import ServerApi

# uri = "mongodb+srv://usernam:<password>@cluster0.kn4aekf.mongodb.net/?retryWrites=true&w=majority"

# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))

# # Send a ping to confirm a successful connection
# try:
# 	client.admin.command('ping')
# 	print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
# 	print(e)


app = Flask(__name__)
CORS(app)


ERROR_LOG = "app.log"
IMG_DIR= os.path.join('C:/Users/USER/ISET/stage experience/img/')
DATE_FORMAT= "%d/%m/%y"
epoch= lambda ch: int(datetime.strptime(ch, DATE_FORMAT).timestamp())

# Create a connection


if True:
    client = MongoClient("mongodb+srv://stage:stage@stage.ldsvqma.mongodb.net/?retryWrites=true&w=majority&appName=stage", server_api=server_api.ServerApi('1'))
else:
    import os
    os.system("'C:/Program Files/MongoDB/Server/7.0/bin/mongod.exe' --dbpath 'C/Users/USER/ISET/stage experience/db'")
    client = MongoClient('mongodb://localhost:27017/')

    import atexit
    atexit.register(lambda:os.system("mongod --shutdown"))


client.admin.command('ping')

db = client['myDatabase']['patients']

# Define the schema
schema = {
    "type" : "object",
    "properties" : {
        "_id" : {"type" : "string"},
        "basic_info" : {
            "type" : "object",
            "properties": {
                "CIN" : {"type" : "string"},
                "name" : {"type" : "string"},
                "birthday" : {"type" : "string", "format": "date"},
                "gender" : {"type" : "string"},
                "address" : {"type" : "string"}
            },
            "required": ["CIN", "name", "birthday", "gender", "address"]
        },
        "image" : {"type" : "string"},
        "knownSicknesses" : {"type" : "array", "items": {"type": "string"}, "default": []},
        "medicalRecord" : {"type" : "array", "items": {
            "type": "object",
            "properties": {
                "doctor" : {"type" : "string"},
                "date" : {"type" : "string", "format": "date"},
                "diagnosis" : {"type" : "string"},
                "medications" : {"type" : "array", "items": {"type": "string"}}
            },
            "required": ["doctor", "date", "diagnosis", "medications"]
        }, "default": []}
    },
    "required": ["_id", "basic_info"]
}

#add patient
# db.insert_one({
# 	"_id": "patient1",
# 	"name": "John Doe",
# 	"birthday": epoch("30/1/1")
# 	"gender": "male",
# 	"address": "123 Main St",

# 	"knownSicknesses": ["Diabetes", "Hypertension"],

# 	"medicalRecord": [
# 		{
# 			"doctor": "Dr. Smith",
# 			"date": epoch("30/1/24")
# 			"diagnosis": "Diabetes",
# 			"medications": ["Metformin"]
# 		},
# 	]
# })

@app.route('/helloworld')
def hello_world():
    return 'Hello World!'

@app.route('/patient/<string:patient_id>', methods=['GET'])
def retrieve_patient(patient_id):
    patient_id= patient_id.lower()
    patient = db.find_one({"_id": patient_id})

    if not patient:
        return {'error': f'Patient with _id {patient_id} does not exist'}, 404

    patient.pop("image")
    return jsonify(patient), 200

@app.route('/patient/<string:patient_id>/image', methods=['GET'])
def get_image(patient_id):
    patient_id= patient_id.lower()
    patient = db.find_one({"_id": patient_id})
    img = patient["image"]

    try:
        return send_file(BytesIO((img)), mimetype='image/jpeg')
    except FileNotFoundError:
        return jsonify({'error': 'Image not found.'}), 404

@app.route('/add_patient', methods=['POST'])
def add_patient():
    data = request.get_json()
    try:
        validate(instance=data, schema=schema)
        db.insert_one(data)
    except ValidationError as e:
        print(f"Invalid data: {e}")
        return {'error': 'invalid format'}, 400

    else:
        print("Data is valid")

    return {'status': 'success'}, 200

@app.route('/patient/<string:patient_id>/update/add_medical_record', methods=['POST'])
def add_medical_record(patient_id):
    patient_id= patient_id.lower()
    data = request.get_json()
    try:
        validate(instance=data, schema=schema['properties']['medicalRecord']['items'])
        db.update_one(
            {"_id": patient_id},
            {"$push": {"medicalRecord": data}}
        )
    except ValidationError as e:
        print(f"Invalid data: {e}")
        return {'error': 'invalid format'}, 404
    else:
        print("Medical record added successfully")

    return {'status': 'success'}, 200

@app.route('/patient/<string:patient_id>/update/sickness', methods=['PUT'])
def update_patient_sicknesses(patient_id):
    patient_id= patient_id.lower()
    sicknesses = request.get_json()

    if not patient_id or not sicknesses:
        return jsonify({'error': 'Missing _id or sicknesses in request body'}),  400

    patient = db.find_one({"_id": patient_id})

    if not patient:
        return jsonify({'error': f'Patient with _id {patient_id} does not exist'}),  404

    db.update_one(
        {"_id": patient_id},
        {"$set": {"knownSicknesses": sicknesses}}
    )

    return jsonify({'status': 'success'}),  200

@app.route('/patient/<string:patient_id>/update/info', methods=['PUT'])
def update_patient_info(patient_id):
    patient_id= patient_id.lower()
    info = request.get_json()

    if not patient_id or not info:
        return jsonify({'error': 'Missing _id or info in request body'}),  400

    patient = db.find_one({"_id": patient_id})

    if not patient:
        return jsonify({'error': f'Patient with _id {patient_id} does not exist'}),  404

    db.update_one(
        {"_id": patient_id},
        {"$set": {"basic_info": info}}
    )

    return jsonify({'status': 'success'}),  200

@app.route('/remove_patient/<string:patient_id>', methods=['DELETE'])
def remove_patient(patient_id):
    patient_id= patient_id.lower()
    result = db.delete_one({"_id": patient_id})

    if result.deleted_count == 0:
        return {'error': f'Patient with _id {patient_id} does not exist'}, 404

    return {'status': 'success'}, 200

@app.route('/patient/<string:patient_id>/update/image', methods=['POST'])
def update_image(patient_id):
    patient_id= patient_id.lower()
    print(request)
    data = request.files['image']
    print(data)

    if not data:
        return {'error': 'No image provided'}, 400

    result = db.update_one(
        {'_id': patient_id}, # Query to find the patient by ID
        {'$set': {'image': data.read()}} # Update operation to set the new image binary string
    )
    if result.modified_count == 1:
        return {'status': 'success'}, 200
    else:
        return {'status': 'fail'}, 400



@app.route('/patient/<string:patient_id>/update/change_id', methods=['PUT'])
def change_id(old_id):
    data = request.get_json()
    new_id = data.get('_id')

    if not new_id:
        return {'error': 'No new ID provided'}, 400

    if db.find_one({"_id": new_id}):
        return {'error': f'Patient with _id {new_id} already exists'}, 400

    db.update_one(
        {"_id": old_id},
        {"$set": {"_id": new_id}}
    )

    return {'status': 'success'}, 200


if __name__ == '__main__':
    try:
        # app.run(host='0.0.0.0', port=5000)
        app.run(
            host='0.0.0.0',
            use_debugger=False,
            passthrough_errors=True,
            debug=True,
            use_reloader=True,
        )
    except KeyboardInterrupt:
        print("Server stopped with CTRL+C")

