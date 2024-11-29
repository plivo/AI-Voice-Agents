export const SessionUpdate = {
    type: "session.update",
    session: {
        turn_detection: {
            type: "server_vad",
            threshold: 0.5,
            prefix_padding_ms: 300,
            silence_duration_ms: 200
        },
        tools: [
            {
                type: "function",
                name: "calc_sum",
                description: "Get the sum of two numbers",
                parameters: {
                    type: "object",
                    properties: {
                        num1: { type: "string", description: "the first number" },
                        num2: { type: "string", description: "the seconds number" }
                    },
                    required: ["num1", "num2"]
                }
            }
        ],
        input_audio_format: "g711_ulaw",
        output_audio_format: "g711_ulaw",
        modalities: ["text", "audio"],
        temperature: 0.8
    }
}