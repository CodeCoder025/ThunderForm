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
    tool_calls_left = 10
    messages = [{"role":"system","content":"""
        You are a CAPTCHA identification agent.

        TASK:
        Inspect the DOM of the currently visible browser page using the available browser tools or screenshot.

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

        Do not return a message directly to the user. Return the classification code using the return_classification_code tool call
"""}, {"role":"user","content":"classify the current page."}]

    schema = CaptchaIdentifierResponse.model_json_schema()
    
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    tools_available.append({"type":"function",
                            "function":{
                                "name":"return_classification_code",
                                "description":"Returns the classification code to the user",
                                "parameters":schema
                            }})
    
    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=tools_available,
            tool_choice="required"
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
            print("CAPTCHA Identification Model Failed to Return with a Tool Call.")
        
        else:
            for tool_call in tool_calls:
                if tool_calls_left == 0:
                    raise RuntimeError("CAPTCHA Solver Agent has run out of tool calls")
                tool_name = tool_call.function.name
                print("CAPTCHA Identifier Agent Called Tool: %s"%tool_name)
                arguments = json.loads(tool_call.function.arguments)

                if tool_name == "return_classification_code":
                    return arguments["classification"]
                
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
    Do not return a message directly to the user. Return the solution to the user using the return_drag_drop_solution function.
    """}]

    schema = drag_drop_solver.model_json_schema()
    exception_counter = 0

    tools = [{"type":"function",
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
                    }},
                    {"type":"function",
                     "function":{
                         "name":"return_drag_drop_solution",
                         "description":"Return the solution to the drag-and-drop CAPTCHA to the user",
                         "parameters":schema
                     }}]

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools= tools,
            tool_choice="required"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Drag-Drop Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if not tool_calls or len(tool_calls) == 0:
            print("Drag-Drop CAPTCHA Solver Failed to Return with Tool Call.")
            messages.append({"role":"system","content":"Do not return a message directly to the user. Return the solution to the drag-and-drop CAPTCHA using the return_drag_drop_solution tool call."})
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

                elif tool_name == "return_drag_drop_solution":
                    solution = {"start_position":{"x":arguments["start_x_position"],
                                                    "y":arguments["response.start_y_position"]},
                                "end_position":{"x":arguments["response.end_x_position"],
                                                "y":arguments["response.end_y_position"]}}
                    return json.dumps(solution)
                
class captcha_solver_response(BaseModel):
    return_code:Literal[0,1] = Field(description="0 = captcha solved successfully; 1 = captcha solving failed")

async def solve_captcha_auto(captcha_key, ai_key, session, captcha_type):
    solver = TwoCaptcha(captcha_key)
    captcha_path = Path(__file__).resolve().parent / "CAPTCHA.jpg"
    captcha_path = captcha_path.as_posix()
    tool_calls_left = 10
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
    Return ONLY using the tool output_return_code. Do not return a message directly to the user.**
"""},
    {"role":"user","content":result}]
    
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    tools_available.append({"type":"function",
                            "function":{
                                "name":"output_return_code",
                                "description":"outputs the return code back to the user",
                                "parameters":schema
                            }})
    exception_counter = 0
    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=tools_available,
            tool_choice="required"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by CAPTCHA Solver Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            print("CAPTCHA Solver Model Failed to Return with Tool Call!")
            messages.append({"role":"system","content":"Do not return a message directly to the user. The return code should be output in the form of a tool call, using the output_return_code tool!"})
            continue
        else:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                print("CAPTCHA Solver Agent Called Tool: %s"%tool_name)
                arguments = json.loads(tool_call.function.arguments)
                if tool_name == "output_return_code":
                    return arguments["return_code"]
                if tool_calls_left == 0:
                    raise RuntimeError("CAPTCHA Solver Agent has run out of tool calls")
                tool_calls_left -= 1
                output = await execute_tool(session, tool_name, arguments)
                messages.append({"role":"tool","tool_call_id":tool_call.id, "content":output})
                messages.append({"role":"system","content":f"""
        You have {tool_calls_left} tool-call rounds remaining.

        You MUST complete your task within this budget.
        Avoid unnecessary tool calls.
        If you have completed the task, immediately return the return code using the required JSON schema."""})