from typing import Dict, List, TypedDict, Optional
from AIControl import transmitAndPost
from pprint import pp
import asyncio
import time
import sys

def typeEffect(text, ex=0.1):
    for char in text:
        time.sleep(ex)
        sys.stdout.write(char)
        sys.stdout.flush()

def async_to_sync(awaitable):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop in the current thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(awaitable)

class Object(TypedDict):
    name: str
    object_type: str
    interactions: Dict[str, str]


class AIInteractionResponse(TypedDict):
    with_: str  # Using with_ since 'with' is a Python keyword
    type: str
    extraData: Optional[str]

class AIResponse(TypedDict):
    focusObject: str
    movementDirectionObject: str 
    interactions: List[AIInteractionResponse]


objects: List[Object] = []
interactions: List[Dict[str, str]] =  []

def modifyInteractionsLoop():
    interactions: Dict[str, str] = {}
    while True:
        typeEffect(f"""
{interactions}

Choose an option:
    (1) Add Another interaction
    (2) Remove last interaction
    (0) Save
""", 0.01)
        res = input(">")
        if int(res) == 0:
            break
        elif int(res) == 1:
            call = input("What do you want to call this interaction?   ")
            value = input("What does this interaction do?   ")
            interactions[call] = value
        elif int(res) == 2:
            interactions.pop(input("What is the name of the interaction to be removed?   "))
            typeEffect("Removed!")
    return interactions


def createObjectLoop():
    newObject: Object = {}
    while True:
        typeEffect(f"""
{newObject}

Choose an option:
    (1) Change name
    (2) Change Type
    (3) Open Interactions Editor
    (0) Save and add
""", 0.01)
        res = input(">")
        if int(res) == 0:
            objects.append(newObject)
            break
        elif int(res) == 1:
            newObject["name"] = input("What do you want to name your new object?   ")
        elif int(res) == 2:
            newObject["object_type"] = input("What is the type of your new object(Living or NonLiving)?   ")
        elif int(res) == 3:
            newObject["interactions"] = modifyInteractionsLoop()

def presentAIOutput(ai_output: AIResponse):
    typeEffect("The AI Moves toward " + ai_output["focusObject"] + "\n")
    time.sleep(1)
    for interaction in ai_output["interactions"]:
        if interaction["extraData"]:
            typeEffect(f"The AI chooses to use '{interaction['type']}' toward {interaction['with_']} and says {interaction['extraData']}\n")
        else:
            typeEffect(f"The AI chooses to {interaction['type']} with {interaction['with_']}\n")
        time.sleep(1)
    typeEffect("That is it.\n")
    time.sleep(3)


def createInteractionLoop():
    interaction = {}
    interaction["from"] = input("What is the object interacting with the AI?   ")
    interaction["type"] = input("What is the type of interaction?   ")
    interaction["description"] = input("Describe the interaction with the AI?   ")
    return interaction
while True:
    typeEffect(f"""
{objects}

{interactions}

Choose an option:
    (1) Create New Object
    (2) Remove Object
    (3) Have an object interact with the AI
    (4) Send Input To AI
    (0) Exit
""", 0.01)
    res = input(">")
    if int(res) == 0:
        break
    elif int(res) == 1:
        createObjectLoop()
    elif int(res) == 2:
        for i, obj in enumerate(objects):
            typeEffect(f"({i}) {obj}")
        typeEffect("Deleted object: ", objects.pop(int(input("Object to delete>"))))
    elif int(res) == 3:
        interactions.append(createInteractionLoop())
    elif int(res) == 4:
        typeEffect("Sending input to AI...")
        result = async_to_sync(transmitAndPost({"objects": objects, "interactionsWithYou": interactions}))
        typeEffect("\n\n\n\n")
        typeEffect("Result: ")
        presentAIOutput(result)
        typeEffect(result)
        interactions = []