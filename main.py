from google.cloud import storage

from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build

from googleapiclient.http import MediaIoBaseDownload
import io
import re

from flask import Flask 
from flask import request
from flask import jsonify

app = Flask(__name__)


service_account_json = "INSERT_SERVICE_ACCOUNT_JSON_FILE_NAME_HERE"
bucket_name = "INSERT_BUCKET_NAME_HERE"


def upload_blob(bucket_name, file_object, source_file_name, destination_blob_name):
  storage_client = storage.Client.from_service_account_json(service_account_json)
  bucket = storage_client.bucket(bucket_name)
  blob = bucket.blob(destination_blob_name)

  # if duplicate name, file gets replaced
  blob.upload_from_string(file_object.getvalue(), content_type="image/png")
  blob.make_public()
  
  # file direct link
  public_url = blob.public_url
  
  print(
    "File {} uploaded to {}.".format(
      source_file_name, destination_blob_name
    )
  )
  return public_url


def download_file(drive_file_id):
  file_id = drive_file_id
  scopes = ['https://www.googleapis.com/auth/drive']
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
    service_account_json, scopes)
  http_auth = credentials.authorize(Http())

  drive_service = build('drive', 'v3', http=http_auth)

  # source file name
  source_file_name = drive_service.files().get(fileId=file_id).execute()['name']
  
  file_object = io.BytesIO()
  request = drive_service.files().get_media(fileId=file_id)
  
  downloader = MediaIoBaseDownload(file_object, request)
  done = False
  while done is False:
    status, done = downloader.next_chunk()
    print("Download {}%.".format(int(status.progress() * 100)))
  
  return source_file_name, file_object


@app.route('/get-public-url', methods=['POST'])
def get_public_url():
  """Endpoint to get image public url from drive file url"""
  if request.method == 'POST':
    drive_file_url = None
    if request.json:
      drive_file_url = request.json.get("fileUrl")
    elif request.form:
      drive_file_url = request.form.get("fileUrl")  

    result = re.search("[-\w]{25,}", drive_file_url)
    drive_file_id = result.group(0)
    print("Drive File Id: " + drive_file_id + "\n")
    
    source_file_name, file_object = download_file(drive_file_id)
    destination_blob_name = source_file_name

    public_url = upload_blob(bucket_name, file_object, source_file_name, destination_blob_name)
    print(public_url)

    return jsonify({"public_url": public_url})

  else:
    error_msg = 'Invalid method'
    return error_msg


if __name__ == '__main__':
  app.run(debug=True)
