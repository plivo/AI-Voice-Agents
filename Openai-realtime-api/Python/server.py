import plivo
from quart import Quart, websocket, Response, request
import asyncio
import websockets
import json
import base64
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env', override=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please add it to your .env file")

PORT = 5000
SYSTEM_MESSAGE = (
    "You are a helpful and a friendly AI assistant who loves to chat about anything the user is interested about."
)

app = Quart(__name__)

@app.route("/webhook", methods=["GET", "POST"])
def home():
    xml_data = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Stream streamTimeout="86400" keepCallAlive="true" bidirectional="true" contentType="audio/x-mulaw;rate=8000" audioTrack="inbound" >
            ws://{request.host}/media-stream
        </Stream>
    </Response>
    '''
    return Response(xml_data, mimetype='application/xml')

@app.websocket('/media-stream')
async def handle_message():
    print('client connected')
    plivo_ws = websocket 
    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    try: 
        async with websockets.connect(url, extra_headers=headers) as openai_ws:
            print('connected to the OpenAI Realtime API')

            await send_Session_update(openai_ws)
            
            receive_task = asyncio.create_task(receive_from_plivo(plivo_ws, openai_ws))
            
            async for message in openai_ws:
                await receive_from_openai(message, plivo_ws, openai_ws)
            
            await receive_task
    
    except asyncio.CancelledError:
        print('client disconnected')
    except websockets.ConnectionClosed:
        print("Connection closed by OpenAI server")
    except Exception as e:
        print(f"Error during OpenAI's websocket communication: {e}")
        
        
        
            
async def receive_from_plivo(plivo_ws, openai_ws):
    try:
        while True:
            message = await plivo_ws.receive()
            data = json.loads(message)
            if data['event'] == 'media' and openai_ws.open:
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": data['media']['payload']
                }
                await openai_ws.send(json.dumps(audio_append))
            elif data['event'] == "start":
                print('Plivo Audio stream has started')
                plivo_ws.stream_id = data['start']['streamId']

    except websockets.ConnectionClosed:
        print('Connection closed for the plivo audio streaming servers')
        if openai_ws.open:
            await openai_ws.close()
    except Exception as e:
        print(f"Error during Plivo's websocket communication: {e}")


async def receive_from_openai(message, plivo_ws, openai_ws):
    try:
        response = json.loads(message)
        print('response received from OpenAI Realtime API: ', response['type'])
        if response['type'] == 'session.updated':
           print('session updated successfully')
        if response['type'] == 'error':
            print('error received from realtime api: ', response)
        elif response['type'] == 'response.audio.delta':
            audio_delta = {
               "event": "playAudio",
                "media": {
                    "contentType": 'audio/x-mulaw',
                    "sampleRate": 8000,
                    "payload": base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                }
            }
            await plivo_ws.send(json.dumps(audio_delta))
        elif response['type'] == 'response.function_call_arguments.done':
            print('received function call response ', response)
            if response['name'] == 'calc_sum':
                output = function_call_output(json.loads(response['arguments']), response['item_id'], response['call_id'])
                await openai_ws.send(json.dumps(output))
                
                generate_response = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["text", "audio"],
                        "temperature": 0.8,
                        "instructions": 'Please share the sum from the function call output with the user'
                    }
                }
                
                print("sending function call response")
                await openai_ws.send(json.dumps(generate_response))
                
        elif response['type'] == 'input_audio_buffer.speech_started':
            print('speech is started')
            clear_audio_data = {
                "event": "clearAudio",
                "stream_id": plivo_ws.stream_id
            }
            await plivo_ws.send(json.dumps(clear_audio_data))
            cancel_response = {
                "type": "response.cancel"
            }
            await openai_ws.send(json.dumps(cancel_response))
    except Exception as e:
        print(f"Error during OpenAI's websocket communication: {e}")
    
    
async def send_Session_update(openai_ws):
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "tools": [
                {
                    "type": "function",
                    "name": "calc_sum",
                    "description": "Get the sum of two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "num1": { "type": "string", "description": "the first number" },
                            'num2': { "type": "string", "description": "the seconds number" }
                        },
                        "required": ["num1", "num2"]
                    }
                }
            ],
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": "alloy",
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8
        }
    }
    await openai_ws.send(json.dumps(session_update))

def function_call_output(arg, item_id, call_id):
    sum = int(arg['num1']) + int(arg['num2'])
    conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "id": item_id,
            "type": "function_call_output",
            "call_id": call_id,
            "output": str(sum)
        }
    }
    return conversation_item

if __name__ == "__main__":
    print('running the server')
    # client = plivo.RestClient(auth_id=os.getenv('PLIVO_AUTH_ID'), auth_token=os.getenv('PLIVO_AUTH_TOKEN'))
    # call_made = client.calls.create(
    #     from_=os.getenv('PLIVO_FROM_NUMBER'),
    #     to_=os.getenv('PLIVO_TO_NUMBER'),
    #     answer_url=os.getenv('PLIVO_ANSWER_XML'),
    #     answer_method='GET',)
    app.run(port=PORT)
    