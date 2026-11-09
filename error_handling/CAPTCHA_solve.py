from twocaptcha import TwoCaptcha
from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json
from pathlib import Path
from io import BytesIO #allows bytes-type files (e.g. images, PDFs) to be handled by memory (computer RAM) rather than having to be written into users hard drive
import base64
from PIL import Image

from interface.browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def screenshot_captcha(session):
    print("Screenshot function called")
    captcha_path = Path(__file__).resolve().parent / "CAPTCHA.jpg"
    captcha_path = captcha_path.as_posix() #converts backslashes to forward slashes, more compatible with some functions

    tool_output = await session.call_tool("browser", 
                                          {"commands": f'screenshot --path "{captcha_path}"'}
    )
    print(tool_output)
async def identify_captcha(ai_key, session):
    client = OpenAI(api_key = ai_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    #Role
    You are a captcha identifier agent.

    #OBJECTIVE:
    By either taking and interpreting a browser screenshot, or inspecting the DOM of the webpage, you are to identify the type of captcha challenge present, if any.

    #INSTRUCTIONS:
    1. Inspect the currently visible browser page.
    2. Identify if there is a CAPTCHA, and if so, what type of captcha is present.
    3. Exit and output with a return code as below

    #CONSTRAINTS:
    Do not scroll, click on any button, or navigate in any way. Your goal is only to identify any captcha in the currently visible browser page.

    #RETRUN CODES:
    - 0: No CAPTCHA challenge available.
    - 1: Normal Captcha (Distorted text on image)
    - 2: Grid Captcha (Involves clicking boxes in a grid)
    - 3: Drag-and-Drop Captcha (Involves item to be dragged into box)

    #OUTPUT:
    Return ONLY a valid JSON object:
    {"return_code":int}
    **Do not provide commentary or explanations.**
"""}]
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=tools_available,
            tool_choice="auto"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by CAPTCHA Identification Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            try:
                model_output = int(json.loads(chat.choices[0].message.content).get("return_code"))
            except:
                messages.append({"role":"user","content":"""Output must be in JSON format of {"return_code":int} only!"""})
                print("CAPTCHA Identifier Agent Failed to Format. Retrying...")
                print(chat.choices[0].message.content)
                continue

            if model_output != 0:
                await screenshot_captcha(session)
                return model_output
        else:
            tool_name = tool_calls[0].function.name
            print("CAPTCHA Identifier Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})

async def solve_drag_drop_captcha(api_key): #need toolos: readfile (bytes)
    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")

    messages = [{"role":"system","content":"""
    # Role
    You are a drag-and-drop CAPTCHA solver agent.

    # Objective
    Identify the correct solution to a drag-and-drop CAPTCHA challenge presented.

    # Workflow
    1. Inspect the file named CAPTCHA.jpg, which is a screenshot of the CAPTCHA challenge.
    2. Understand the demands of the drag-and-drop CAPTCHA challenge (e.g. dragging the given number into the box, dragging the correct shape to fit into the image, etc)
    3. Identify the correct element to drag.
    4. Identify the correct position to drop the element.
    5. Return the coordinates of the position to drag from and drop to.

    #Coordinate Units
    Coordinate units are in CSS pixels relative to the viewport, NOT physical screen pixels. Origin (0,0): top left corner of browser viewport. 

    # Output Format
    Return ONLY valid JSON, and nothing else:

    ```json
    {"start_position":{"x":int, "y":int},
     "end_position":{"x":int, "y":int}}
    """}]

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools= {"type":"function",
                    "function":{
                        "name":"ReadFile",
                        "description":"Read the data stored in a file (bytes or text, depending on file type)",
                        "parameters":{
                            "required":["file_path"],
                            "type":"object",
                            "properties":{
                                "file_path":{
                                    "type":"string",
                                    "description":"Path of file to read"
                                }
                            }
                        }
                    }}
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Drag-Drop Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if not tool_calls or len(tool_calls) == 0:
            output = chat.choices[0].message.content
            try:
                solution = json.loads(output)
                return solution
            except:
                if output.startswith("```json") and output.endswith("```"):
                    _, back = output.split("n")
                    middle, _ = back.split("`")
                    return str(middle)
                
                messages.append({"role":"user","content":f"""Ouptut must be in JSON format of {{"start_position":{{"x":int, "y":int}},
                     "end_position":{{"x":int, "y":int}}}} only, previous output was of type {type(output)}"""})
                print(output)
                print("Drag-Drop Agent Failed to Format. Retrying...")
                continue
        else:
            tool_name = tool_calls[0].function.name
            print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
            arguments = json.loads(tool_calls[0].function.arguments)
            if tool_name == "ReadFile":
                with open(arguments["file_path"], "r") as image_file:
                    content = image_file.read()
                messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":content})

async def solve_captcha_auto(captcha_key, ai_key, session, captcha_type):
    solver = TwoCaptcha(captcha_key)
    captcha_path = Path(__file__).resolve().parent / "CAPTCHA.jpg"
    captcha_path = captcha_path.as_posix()
    
    if captcha_type == 1:
        response = solver.normal(str(captcha_path)) #returns text
        specific_instruction = "For a normal captcha (scrambled/messy text), a string of the text will be given as the solution."
        result = response.get("code") 
    elif captcha_type == 2:
        response = solver.grid(str(captcha_path)) #returns numbers of boxes
        solution = response.get("solution").get("click")
        specific_instruction = "For grid captcha (requires selection of boxes in a grid), numbers representing the boxes to select will be given to you."
        result = str(solution)
    elif captcha_type == 3:
        response = solve_drag_drop_captcha(ai_key, session)
        specific_instruction = """For drag and drop captcha (requires dragging some element into a box), {"start_position":{"x":int, "y":int},
                     "end_position":{"x":int, "y":int}} will be given to you. You are to drag the item from the start coordinate to the end coordinate of the user's screen. Start and end coordinates are in terms of CSS pixels relative to the browser viewport of the user, with the origin (0,0) being the top left corner of the user's browser window."""

    client = OpenAI(api_key = ai_key, base_url = "https://openrouter.ai/api/v1")
        
    messages = [{"role":"system","content":f"""
    #Role
    You are a captcha executor agent.

    #OBJECTIVE:
    Given the correct answer to the captcha, you are to solve the captcha challenge displayed on the user's screen.

    #Workflow:
    1. Examine the user's browser, and the captcha solution given to you.
    2. Interact with the captcha challenge using the solution given. {specific_instruction}
    3. Exit and return a code based on whether or not the CAPTCHA has been successfully solved.
    
    #RETRUN CODES:
    - 0: CAPTCHA solved successfully
    - 1: CAPTCHA solve failed

    #OUTPUT:
    Return ONLY a valid JSON object:
    {{"return_code":int}}
    **Do not provide commentary or explanations.**
"""},
    {"role":"user","content":result}]
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=tools_available,
            tool_choice="auto"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by CAPTCHA Solver Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            try:
                model_output = int(json.loads(chat.choices[0].message.content).get("return_code"))
            except:
                messages.append({"role":"user","content":f"""Output must be in JSON format of {{"return_code":int}} only, previous output was of type {type(model_output)}!"""})
                print("CAPTCHA Solver Agent Failed to Format. Retrying...")
                continue

            return model_output
        else:
            tool_name = tool_calls[0].function.name
            print("CAPTCHA Solver Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})
