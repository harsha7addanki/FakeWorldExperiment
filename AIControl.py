from dotenv import load_dotenv; load_dotenv()
from google import genai
import asyncio
import json
import os


# print("Connecting to Google AI Studio...")
client = genai.Client(api_key=os.environ.get("GOOGLE_GENAI_API_KEY"), http_options={'api_version':'v1alpha'})
# print("Connected to Google AI Studio.")
# print("Creating chat session...")
chat = client.aio.chats.create(
    model='gemini-2.0-flash-thinking-exp',
)
# print("Chat session created.")

print('Sending AI basic briefing...')
asyncio.run(chat.send_message('you are connected to a robot you have multipule sensors and other AI systems working in conjunction with you. some of which can act as your motor control, an object detection model to serve as your eyes and much more. you will be given what you see in JSON format and therefore you respond in the following json schema:{"$schema": "http://json-schema.org/draft-04/schema#","type": "object","properties": {"focusObject": {"type": "string"},"movementDirectionObject": {"type": "string"},"interactions": {"type": "array","items": [{"type": "object","properties": {"with_": {"type": "string"},"type": {"type": "string"}, "extraData":{"type":"string"}},"required": ["with_","type"]}]}},"required": ["focusObject","movementDirectionObject","interactions"]}. also when you respond with the object to interact with you MUST use the full name given to you of the object or the movement core will not work. Also the extra parameters for interaction is used for what to say when talking so when you respond put what you would say in that field. The extraData is STRICTLY only for use when needed such as when talking or specifically requested by the interaction.'))


def solve_fast(s):
    ind1 = s.find('\n')
    ind2 = s.rfind('\n')
    return s[ind1+1:ind2]

async def transmitAndPost(tosend: dict):
    tosend = json.dumps(tosend)
    # print("Received JSON: ", tosend)
    # print("Sending JSON to AI...")
    # print("JSON sent to AI.")
    response = await chat.send_message(tosend)
    # print("AI response received.")
    trimedResponse = solve_fast(response.text)
    print("Trimmed AI response: ", trimedResponse)
    return json.loads(trimedResponse)
