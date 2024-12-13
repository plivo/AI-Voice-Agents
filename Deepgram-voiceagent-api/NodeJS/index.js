import { Client } from "plivo";
import WebSocket, { WebSocketServer } from 'ws';
import express from "express";
import http from 'http'
import { SettingsConfiguration } from "./SettingsConfiguration.js";
import dotenv from "dotenv";
import { getWeatherFromCityName } from "./functionCall.js";


dotenv.config();
const app = express()
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
let streamId = ""

const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

let client;
const PORT = 5000;

const { DEEPGRAM_API_KEY } = process.env

SettingsConfiguration.agent.think.instructions = 'You are a helpful and a friendly AI assistant who loves to chat about anything the user is interested about.';



app.post("/webhook", (request, reply) => {
  console.log('reques host is ', request.host)
  const PlivoXMLResponse = `<?xml version="1.0" encoding="UTF-8"?>
                              <Response>
                                  <Stream streamTimeout="86400" keepCallAlive="true" bidirectional="true" contentType="audio/x-mulaw;rate=8000" audioTrack="inbound" >
                                      ws://${request.host}/media-stream
                                  </Stream>
                              </Response>`;

  reply.type('text/xml').send(PlivoXMLResponse);
})

server.on('upgrade', (request, socket, head) => {
  if (request.url === '/media-stream') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  } else {
    socket.destroy();
  }
});

const sendUpdateInstructions = (deepgramWs) => {
    deepgramWs.send(JSON.stringify(SettingsConfiguration))
}

const itemForFunctionOutput = (arg, itemId, callId) => {
  const sum = parseInt(arg.num1) + parseInt(arg.num2)
  const conversationItem = {
    type: "conversation.item.create",
    previous_item_id: null,
    item: {
      id: itemId,
      type: "function_call_output",
      call_id: callId,
      output: sum.toString(),
    }
  }
  return conversationItem;
}

const startDeepgramWSConnection = (plivoWS) => {
  const deepgramWs = new WebSocket('wss://agent.deepgram.com/agent', {
    headers: {
      "Authorization": "Token " + DEEPGRAM_API_KEY,
    }
  })

  deepgramWs.on('open', () => {
    console.log('DeepGram websocket connected')
    // setTimeout(() => {
      sendUpdateInstructions(deepgramWs)
    // }, 250)
  })

  deepgramWs.on('close', () => {
    console.log('Disconnected from the DeepGram API')
  });

  deepgramWs.on('error', (error) => {
    console.log('Error in the DeepGram Websocket: ', error)
  })

  deepgramWs.on('message', async (message, isBinary) => {
    try {
        if (isBinary) {
            const audioDelta = {
                event: 'playAudio',
                media: {
                  contentType: 'audio/x-mulaw',
                  sampleRate: 8000,
                  payload: Buffer.from(message, 'base64').toString('base64')
                }
              }
              plivoWS.send(JSON.stringify(audioDelta));
        } else {
            const response = JSON.parse(message)
            switch (response.type) {
                case 'SettingsApplied':
                    console.log('Settings successfully applied')
                    break;
                case 'Welcome':
                    console.log('Received welcome message')
                    break;
                case 'UserStartedSpeaking':
                    console.log('speech is started')
                    const data = {
                        "event": "clearAudio",
                        "stream_id": streamId
                    }
                    plivoWS.send(JSON.stringify(data))
                    break;
                case 'FunctionCallRequest':
                    console.log('Function call request received for getNameFromNumber')
                    if (response.function_name === 'getWeatherFromCityName') {
                        const output = await getWeatherFromCityName(response.input.city, process.env.OPENWEATHERMAP_API_KEY)

                        const functionCallResponse = {
                            "type": "FunctionCallResponse",
                            "function_call_id": response.function_call_id, 
                            "output": output
                          }
                        deepgramWs.send(JSON.stringify(functionCallResponse))
                    }
                    break;
                default:
                    console.log('Response received from the DeepGram API is ', response)
            }
        }


    } catch (error) {
      console.error('Error processing DeepGram message: ', error, 'Raw message: ', message)
    }
  });
  return deepgramWs
}

wss.on('connection', (connection) => {
  console.log('Client connected to WebSocket');

  // start the DeepGram websocket connection
  const deepgramWs = startDeepgramWSConnection(connection);

  let audioBuffer = []

  connection.on('message', (message) => {
    try {
      const data = JSON.parse(message)
      switch (data.event) {
        case 'media':
          if (deepgramWs && deepgramWs.readyState === WebSocket.OPEN) {
              deepgramWs.send(Buffer.from(data.media.payload, 'base64'))
          }
          break;
        case 'start':
          console.log('Incoming stream has started')
          streamId = data.start.streamId
          console.log('Stream ID is ', streamId)
          break;
        default:
          console.log('Received non-media evengt: ', data)
          break
      }
    } catch (error) {
      console.error('Error parsing message: ', error, 'Message: ', message)
    }
  });

  connection.on('close', () => {
    if (deepgramWs.readyState === WebSocket.OPEN) deepgramWs.close();
    console.log('client disconnected')
  });


});


server.listen(PORT, () => {
  console.log('server started on port 5000')
  client = new Client(process.env.PLIVO_AUTH_ID, process.env.PLIVO_AUTH_TOKEN)
  let response = client.calls.create(
    process.env.PLIVO_FROM_NUMBER,
    process.env.PLIVO_TO_NUMBER,
    process.env.PLIVO_ANSWER_XML,
    { answerMethod: "GET" })
    .then((call) => {
      console.log('call created ', call)
    }).catch((e) => {
      console.log('error is ', e)
    })
})