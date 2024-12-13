export const SettingsConfiguration = {
    "type": "SettingsConfiguration",
    "audio": {
      "input": { 
        "encoding": "mulaw",
        "sample_rate": 8000
      },
      "output": { 
        "encoding": "mulaw",
        "sample_rate": 8000,
        "container": "none",
      }
    },
    "agent": {
      "listen": {
        "model": "nova-2" 
      },
      "think": {
        "provider": {
          "type": "open_ai" 
        },
        "model": "gpt-3.5-turbo", 
        "instructions": "You are a helpful assistant.", 
        "functions": [
        {
          "name": "getWeatherFromCityName",
          "description": "Get the weather from the given city name",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {
                "type": "string",
                "description":"The city name to get the weather from" 
              }
            },
            "required": ["city"]
          },
        }
        ]
      },
      "speak": {
        "model": "aura-asteria-en" 
      }
    }
  }