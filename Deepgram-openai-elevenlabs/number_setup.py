import json
import sys
from plivo import plivoxml
import plivo
import xml.etree.ElementTree as ET
import requests

CONFIG = {}


def load_config(file_path='config.json'):
    global CONFIG
    with open(file_path, 'r') as f:
        CONFIG = json.load(f)


def create_xml(ws_url):
    response = plivoxml.ResponseElement().add(
        plivoxml.StreamElement(ws_url,
                               bidirectional="true",
                               audioTrack="inbound",
                               keepCallAlive="true",
                               contentType="audio/x-l16;rate=8000"))
    return response.to_string()


def upload_xml(xml_string):
    # Gist API endpoint
    url = "https://api.github.com/gists"

    # Headers for authorization
    headers = {
        "Authorization": f"token {CONFIG['github_token']}",
        "Accept": "application/vnd.github.v3+json"
    }

    filename = "voicebot.xml"  # Change this to your desired filename

    # Gist payload
    data = {
        "description": "XML file created via Python script",
        "public": False,  # Set to True if you want the Gist to be public
        "files": {
            filename: {
                "content": xml_string
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        gist_info = response.json()

        # Extract the raw_url dynamically using the filename
        raw_url = gist_info['files'][filename]['raw_url']
        return True, raw_url
    else:
        print(f"Failed to create Gist. Status Code: {response.status_code}")
        print(response.text)
        return False, ''


def create_application(xml_url):
    client = plivo.RestClient(CONFIG['auth_id'], CONFIG['auth_token'])
    response = client.applications.create(
        app_name='voice-bot-application',  # Change this to your desired application name
        answer_url=xml_url,
        answer_method='GET'
    )

    return response['app_id']


def update_phone_number(phoneNumber, appId):
    client = plivo.RestClient(CONFIG['auth_id'], CONFIG['auth_token'])
    number = client.numbers.get(
        number=phoneNumber, )
    response = number.update(
        app_id=appId, )

    if response['message'] == 'changed':
        return True

    return False


if __name__ == "__main__":
    phoneNumber = sys.argv[1]
    url = sys.argv[2]

    load_config()

    xmlString = create_xml(url)
    xmlUploaded, xml_url = upload_xml(xmlString)
    if xmlUploaded:
        appId = create_application(xml_url)
        update_phone_number(phoneNumber, appId)
        print("Number setup completed")
    else:
        print("Number setup failed as xml could not be uploaded")
