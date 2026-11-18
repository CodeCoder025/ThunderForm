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
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal #restricts a variable or a return value to be only specific values (otherwise raises error)

from interface.browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def screenshot_captcha(session):
    print("Screenshot function called")
    captcha_path = Path(__file__).resolve().parent / "CAPTCHA.jpg"
    captcha_path = captcha_path.as_posix() #converts backslashes to forward slashes, more compatible with some functions

    tool_output = await session.call_tool("browser", 
                                          {"commands": f'screenshot --path "{captcha_path}"'}
    )
    print(tool_output)

class CaptchaIdentifierResponse(BaseModel):
    model_config = ConfigDict(extra="forbid") #reject any extra fields
    classification: Literal[0,1,2,3] = Field(
        description = "0 = No CAPTCHA challenge; 1 = Text CAPTCHA; 2 = Grid CAPTCHA; 3 = Drag-and-Drop CAPTCHA"
    )

async def identify_captcha(ai_key, session):
    client = OpenAI(api_key = ai_key, base_url = "https://openrouter.ai/api/v1")
    tool_calls_left = 5
    messages = [{"role":"system","content":"""
        You are a CAPTCHA identification agent.

        TASK:
        Inspect the currently visible browser page using the available browser tools or screenshot.

        Determine whether a CAPTCHA challenge is visibly present.

        CLASSIFICATION:
        - 0: No CAPTCHA challenge or any challenge meant to prevent bots.
        - 1: Text CAPTCHA (distorted text in an image).
        - 2: Grid CAPTCHA (selecting tiles in a grid).
        - 3: Drag-and-drop CAPTCHA, or any visual drag-and-drop challenge (need not be official CAPTCHA)

        RESTRICTIONS:
        - Do not scroll, click, type, or navigate.
        - Only inspect the currently visible page.
        - Do not attempt to solve any CAPTCHA.
        - If no CAPTCHA is detected, return code 0.
        - If uncertain, return code 0.

        Follow the response schema provided by the API. Do not include side text or explainations outside the structured response
"""}]

    schema = CaptchaIdentifierResponse.model_json_schema()
    
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    exception_counter = 0
    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=tools_available,
            tool_choice="auto",
            response_format = {
                "type":"json_schema",
                "json_schema":{
                    "name":"captcha_identification_response",
                    "strict":True,
                    "schema":schema
                }
            }
        )
        choice = chat.choices[0]

        print("Finish reason:", choice.finish_reason)
        print("Tool calls:", len(choice.message.tool_calls or []))
        print("Content:", choice.message.content)

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by CAPTCHA Identification Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            output = chat.choices[0].message.content
            try:
                result = CaptchaIdentifierResponse.model_validate_json(output)
                model_output = result.model_dump().get("classification")
                
            
            except:
                message = chat.choices[0].message

                print("Finish reason:", chat.choices[0].finish_reason)
                print("Refusal:", message.refusal)
                print("Content:", repr(message.content))
                if exception_counter == 5:
                    raise RuntimeError("CAPTCHA Identifier Agent returned with more than 5 exceptions!")
                messages.append({"role":"user","content":"""Follow the output guideline given in the API schema!"""})
                print("CAPTCHA Identifier Agent Failed to Format. Retrying...")
                print(chat.choices[0].message.content)
                exception_counter+=1
                continue

            if model_output != 0:
                await screenshot_captcha(session)
            return model_output
        
        else:
            for tool_call in tool_calls:
                if tool_calls_left == 0:
                    raise RuntimeError("CAPTCHA Solver Agent has run out of tool calls")
                tool_name = tool_call.function.name
                print("CAPTCHA Identifier Agent Called Tool: %s"%tool_name)
                arguments = ast.literal_eval(tool_call.function.arguments)
                output = await execute_tool(session, tool_name, arguments)
                messages.append({"role":"tool","tool_call_id":tool_call.id, "content":output})
                tool_calls_left -= 1
                messages.append({"role":"system","content":f"""
        You have {tool_calls_left} tool-call rounds remaining.

        You MUST complete your task within this budget.
        Avoid unnecessary tool calls.
        If you have sufficient information, immediately return
        your classification using the required JSON schema."""})

class drag_drop_solver(BaseModel):

    model_config = ConfigDict(extra="forbid")
    start_x_position:int = Field(description="x-value of CSS coordinate position of intitial starting position of item to drag")
    start_y_position:int = Field(description="y-value of CSS coordinate position of intitial starting position of item to drag")
    end_x_position:int = Field(description="x-value of CSS coordinate position of final ending position of item to drag, i.e. coordinates to drag item to")
    end_y_position:int = Field(description="y-value of CSS coordinate position of final ending position of item to drag, i.e. coordinates to drag item to")

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
    Return ONLY one valid JSON object, based on the format of the JSON schema given to you in the API call.
    Note that the return format takes in each the x and y coordinate in separate fields, for both the start and end position.
    """}]

    schema = drag_drop_solver.model_json_schema()
    exception_counter = 0

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools= [{"type":"function",
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
                    }}],
            response_format={
                "type":"json_schema",
                "json_schema":{
                    "name":"drag_and_drop_coordinates",
                    "strict":True,
                    "schema":schema
                }
            }
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Drag-Drop Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if not tool_calls or len(tool_calls) == 0:
            output = chat.choices[0].message.content
            try:
                response = drag_drop_solver.model_validate_json(output)
                solution = {"start_position":{"x":response.start_x_position,
                                                "y":response.start_y_position},
                            "end_position":{"x":response.end_x_position,
                                            "y":response.end_y_position}}
                return json.dumps(solution)
            except:
                exception_counter += 1
                if exception_counter == 6:
                    raise RuntimeError("Drag-and-Drop Captcha Solver returned more than 5 exceptions")
                messages.append({"role":"user","content":f"""Ouptut must be in JSON format of {schema}"""})
                print(output)
                print("Drag-Drop Agent Failed to Format. Retrying...")
                continue

        else:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
                arguments = json.loads(tool_call.function.arguments)
                if tool_name == "ReadFile":
                    with open(arguments["file_path"], "rb") as image_file:
                        content = image_file.read()
                    messages.append({"role":"tool","tool_call_id":tool_call.id, "content":content})
class captcha_solver_response(BaseModel):
    return_code:Literal[0,1] = Field(description="0 = captcha solved successfully; 1 = captcha solving failed")

async def solve_captcha_auto(captcha_key, ai_key, session, captcha_type):
    solver = TwoCaptcha(captcha_key)
    captcha_path = Path(__file__).resolve().parent / "CAPTCHA.jpg"
    captcha_path = captcha_path.as_posix()
    tool_calls_left = 5
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
    
    schema = captcha_solver_response.model_json_schema()
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
    Return ONLY a valid JSON object, in the form stated in the json schema given in the API call.
    Do not add any commentary, supplementary text, or markdown fencing.**
"""},
    {"role":"user","content":result}]
    
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    exception_counter = 0
    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=tools_available,
            tool_choice="auto",
            response_format = {"type":"json_schema",
                               "json_schema":{
                                   "name":"captcha_automatic_solver",
                                   "strict":True,
                                   "schema":schema
                               }}
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by CAPTCHA Solver Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            try:
                model_output = captcha_solver_response.model_validate_json(chat.choices[0].message.content).return_code
            except:
                exception_counter += 1
                if exception_counter == 6:
                    raise RuntimeError("Captcha Solver Agent returned with more than 5 exceptions")
                messages.append({"role":"user","content":f"""Output must be in JSON schema format of {schema}!"""})
                print("CAPTCHA Solver Agent Failed to Format. Retrying...")
                continue

            return model_output
        else:
            for tool_call in tool_calls:
                if tool_calls_left == 0:
                    raise RuntimeError("CAPTCHA Solver Agent has run out of tool calls")
                tool_calls_left -= 1
                tool_name = tool_call.function.name
                print("CAPTCHA Solver Agent Called Tool: %s"%tool_name)
                arguments = ast.literal_eval(tool_call.function.arguments)
                output = await execute_tool(session, tool_name, arguments)
                messages.append({"role":"tool","tool_call_id":tool_call.id, "content":output})
                messages.append({"role":"system","content":f"""
        You have {tool_calls_left} tool-call rounds remaining.

        You MUST complete your task within this budget.
        Avoid unnecessary tool calls.
        If you have completed the task, immediately return the return code using the required JSON schema."""})