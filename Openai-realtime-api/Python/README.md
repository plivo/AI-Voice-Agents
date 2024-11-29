# Plivo Audio Streaming Integration with OpenAI's Realtime API

This project demonstrates integrating Plivo's audio streaming with OpenAI's Realtime Speech to Speech(S2S) model. The system is designed to act as a general Voice AI assistant that can take the raw audio as input, send the captured audio to the OpenAI's realtime model and then respond back in the form of raw audio which is then played by the plivo to the user.

## Features

1. Receive audio streaming data from Plivo through an exposed websocket.
2. Communicate with the OpenAi's realtime model through voice.
3. Handle interruption in speech.
4. Demonstrate function calling support whenever required.
5. Receive the audio from the OpenAI's realtime model and send it back to the plivo server through the exposed Audio streaming websocket .
6. Play the audio to the user.

### Prerequisites
To use the app, you will  need:

- **Python** We used \`3.10.5\` for development; download from [here](https://www.python.org/downloads/).
- **A Plivo account.** You can sign up for a free trial [here](https://console.plivo.com/accounts/request-trial/).
- **A Plivo number with _Voice_ capabilities.** [Here are instructions](https://www.plivo.com/docs/numbers/guides/buy-a-number/) to purchase a phone number.
- **An OpenAI account and an OpenAI API Key.** You can sign up [here](https://platform.openai.com/).
  - **OpenAI Realtime API access.**

### How to setup locally?

### 1. Open an ngrok tunnel
When developing & testing locally, you'll need to open a tunnel to forward requests to your local development server. These instructions use ngrok.

Open a Terminal and run:
```
ngrok http 5000
```

Once the tunnel has been opened, copy the `Forwarding` URL. It will look something like: `https://[your-ngrok-subdomain].ngrok.app`. You will
need this when creating the Plivo Answer XML.

Note that the `ngrok` command above forwards to a development server running on port `5000`, which is the default port configured in this application. If
you override the `PORT` defined in `server.py`, you will need to update the `ngrok` command accordingly.

Keep in mind that each time you run the `ngrok http` command, a new URL will be created, and you'll need to update it everywhere it is referenced below.

### 2. Install required packages: 
```
pip install -r requirements.txt
```

### 3. Update the .env file

#### Creat the Answer XML
A pre-defined answer XML(**PLIVO_ANSWER_XML**) is present in the **.env** file. You can copy the XML and replace the redirect url with your ngrok url. For Example, `https://[your-ngrok-subdomain].ngrok.app/webhook`.

Once done, replace the **PLIVO_ANSWER_XML** present in the .env file with you own answer xml url.

#### Add Plivo credentails
Update the other variables present in the **.env** file such as

```
PLIVO_AUTH_ID=<YOUR_PLIVO_AUTH_ID>
PLIVO_AUTH_TOKEN=<YOUR_PLIVO_AUTH_TOKEN>
PLIVO_FROM_NUMBER=<YOUR_PLIVO_NUMBER>
PLIVO_TO_NUMBER=<CALLER_PHONE_NUMBER>
```

#### Add the OpenAI API key
In the .env file, update the OPENAI_API_KEY to your OpenAI API key from the Prerequisites.

```
OPENAI_API_KEY=<YOUR_OPEN_AI_API_KEY>
```

## Run the app
Once ngrok is running, dependencies are installed,  `.env` is set up, run the dev server with the following command:
```
python server.py
```

With the development server running, Call will be initiated automatically to the `PLIVO_TO_NUMBER`. After the call is answered, you should be able to talk to the AI Assistant. Have fun!