# Plivo Audio Streaming Integration with Deepgram, OpenAI, and ElevenLabs

This project demonstrates a proof of concept (POC) for integrating Plivo's audio streaming with Deepgram for transcription, OpenAI for conversational responses, and ElevenLabs for text-to-speech conversion. The system is designed to act as a general assistant that can transcribe live audio, respond to queries, and convert responses back to audio.

## Features

1. Receive audio streaming data from Plivo through an exposed websocket.
2. Buffer audio until a pause of more than 500ms is detected using voice activity detection.
3. Send the buffered audio to Deepgram for transcription.
4. Send the transcription to OpenAI to generate a response.
5. Convert the response to speech using ElevenLabs.
6. Send the converted speech back to Plivo.

### Prerequisites
Sign up for the following services and get an API key for each:
* [Deepgram](https://console.deepgram.com/signup)
* [OpenAI](https://platform.openai.com/signup)
* [ElevenLabs](https://elevenlabs.io/app/sign-up)

### How to setup locally?

### 1. Create a virtual environment named `venv`
```
pip install virtualenv
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate
```

### 2. Install requirements: 
```
pip install -r requirements.txt`
```

### 3. Start an [ngrok](https://ngrok.com) tunnel for port `5000`:
As we are running this application locally, we'll need to open a tunnel to forward requests to the local development server. In this setup, we are using ngrok.

Open terminal and run:
```
ngrok http 5000
```
Once the tunnel has been opened, copy the Forwarding URL. It will look something like: https://[your-ngrok-subdomain].ngrok.app or https://[your-ngrok-subdomain].ngrok-free.app if you are using free version (eg. https://2073-49-207-221-93.ngrok-free.app). You will need this when creating the Plivo Answer XML.

### 4. Install 'ffmpeg'
FFmpeg is a versatile open-source software suite for processing, converting, and streaming audio and video files. Please visit [here](https://www.ffmpeg.org/download.html) to download and install

### 5. Configure Environment Variables
Update `config.json` to add uour credentials:
```
{
    "auth_id": "your_auth_id",
    "auth_token": "your_auth_token",
    "github_token": "your_github_token",
    "deepgram_api_key": "your_deepgram_api_key",
    "openai_api_key": "your_openai_api_key",
    "elevenlabs_api_key": "your_elevenlabs_api_key"
}
```
If you do not have a GitHub token, you can generate one by following steps mentioned [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens). When creating the token, please make sure that it has Read and Write permission for Gists

### 6. Define your chatbot's behavior
In `server.py`, you can define the characteristics of your voice bot by updating the **system_msg**.
```
system_msg = """You are John Doe, a chatbot assistant that helps in resolving general queries related to any fields.
When someone says hello, you will greet them and answer their questions in a polite way.
"""
```
A system message in OpenAI provides instructions that guide the behavior, tone, and style of the model, ensuring consistent and contextually appropriate responses throughout the conversation. It's crucial for setting the model's role and defining the interaction parameters, helping tailor the AI's output to specific use cases or user requirements.

### 7. Start your server
```
python server.py
```

### 8. Configure Incoming phone number
Configure an active phone number by using  [Plivo Console](https://console.plivo.com/active-phone-numbers/)

You can also execute below command to configure your number
```commandline
 python number_setup.py your-plivo-number ws://[your-ngrok-subdomain].ngrok.app/stream
```
In the command, replace "your-plivo-number" with your Plivo number and "[your-ngrok-subdomain].ngrok.app" with the Forwarding URL generated in step 3 (eg. "ws://2073-49-207-221-93.ngrok-free.app/stream").

### 9. Testing your Application
You are now all set to test your application and converse with a Voice Bot🤖. Just place a call to the Plivo number you have configured for your setup, and connect to your AI based Voice Agent.

## Application Workflow
Voicebot coordinates the data flow between multiple different services including Plivo Audio Streams, Deepgram, OpenAI and Eleven Labs:
![Voicebot Flow](./Workflow.png)

## Logs
![Logs](./demo.gif)
