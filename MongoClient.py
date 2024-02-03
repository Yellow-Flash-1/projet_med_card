from jsonschema import validate, ValidationError
from pymongo import MongoClient
from datetime import *
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from traceback import print_exc

app = Flask(__name__)
CORS(app)

import os
os.system("""
	& 'C:\\Program Files\\MongoDB\\Server\\7.0\\bin\\mongod.exe' --dbpath 'C:\\Users\\USER\\ISET\\stage experience\\db'
""")

ERROR_LOG = "app.log"
IMG_DIR= os.path.join('C:\\Users\\USER\\ISET\\stage experience\\img')
DATE_FORMAT= "%d/%m/%y"
epoch= lambda ch: int(datetime.strptime(ch, DATE_FORMAT).timestamp())

# Create a connection
client = MongoClient('mongodb://localhost:27017/')

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


@app.route('/patient/<string:patient_id>', methods=['GET'])
def retrieve_patient(patient_id):
	patient = db.find_one({"_id": patient_id})

	if not patient:
		return {'error': f'Patient with _id {patient_id} does not exist'}, 404

	return jsonify(patient), 200

@app.route('/patient/<string:patient_id>/image', methods=['GET'])
def get_image(patient_id):
	patient = db.find_one({"_id": patient_id})
	image_path = os.path.join(IMG_DIR, patient["image"])

	if not os.path.isfile(image_path):
		return jsonify({'error': 'Image not found.'}), 404

	return send_file(image_path, mimetype='image/jpeg')

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

@app.route('/patient/<string:patient_id>/update/add_sickness', methods=['POST'])
def update_patient_add_sickness(patient_id):
	data = request.get_json()
	sickness = data.get('sickness')

	if not patient_id or not sickness:
		return {'error': 'Missing _id or sickness in request body'}, 400

	patient = db.find_one({"_id": patient_id})

	if not patient:
		return {'error': f'Patient with _id {patient_id} does not exist'}, 404

	db.update_one(
		{"_id": patient_id},
		{"$push": {"knownSicknesses": sickness}}
	)

	return {'status': 'success'}, 200

@app.route('/patient/<string:patient_id>/update/remove_sickness/<string:sickness>', methods=['DELETE'])
def remove_sickness(patient_id, sickness):
	patient = db.find_one({"_id": patient_id})

	if not patient:
		return {'error': f'Patient with _id {patient_id} does not exist'}, 404

	if sickness not in patient['knownSicknesses']:
		return {'error': f'Sickness {sickness} does not exist in patient\'s knownSicknesses'}, 404

	db.update_one(
		{"_id": patient_id},
		{"$pull": {"knownSicknesses": sickness}}
	)

	return {'status': 'success'}, 200

@app.route('/remove_patient/<string:patient_id>', methods=['DELETE'])
def remove_patient(patient_id):
	result = db.delete_one({"_id": patient_id})

	if result.deleted_count == 0:
		return {'error': f'Patient with _id {patient_id} does not exist'}, 404

	return {'status': 'success'}, 200

@app.route('/patient/<string:patient_id>/update/update_image', methods=['PUT'])
def update_image(patient_id):
	data = request.get_json()
	image = data.get('image')

	if not image:
		return {'error': 'No image provided'}, 400

	db.update_one(
		{"_id": patient_id},
		{"$set": {"image": image}}
	)

	return {'status': 'success'}, 200

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
	with open(ERROR_LOG, mode='a') as f:
		try:
			# app.run(host='0.0.0.0', port=5000)
			app.run(
				use_debugger=False,
				passthrough_errors=True,
				debug=True,
				use_reloader=True,
			)
		except KeyboardInterrupt:
			print("Server stopped with CTRL+C")
		except Exception as e:
			f.write(datetime.now().strftime("%Y%m%d%H%M%S") + "  ")
			print_exc(file=f)

