from twocaptcha import TwoCaptcha
from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json

from interface.browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def identify_captcha(ai_key, session):
    client = OpenAI(api_key = ai_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    #Role
    You are a captcha identifier agent.

    #OBJECTIVE:
    By either taking and interpreting a browser screenshot, or inspecting the DOM of the webpage, you are to identify the type of captcha challenge present, if any.
    You are to then save a browser screenshot of the Captcha challenge as .jpg file in this directory, and name it CAPTCHA.jpg

    #INSTRUCTIONS:
    1. Inspect the currently visible browser page.
    2. Identify if there is a CAPTCHA, and if so, what type of captcha is present.
    3. Exit and output with a return code as below

    #RETRUN CODES:
    - 0: No CAPTCHA challenge available.
    - 1: Normal Captcha (Distorted text on image)
    - 2: Grid Captcha (Involves clicking boxes in a grid)

    #OUTPUT:
    Return ONLY a valid JSON object:
    {"return code":int}
    **Do not provide commentary or explanations.**
"""}]
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
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
                model_output = int(json.loads(chat.choices[0].message.content).get("return code"))
            except:
                messages.append({"role":"user","content":"""Output must be in JSON format of {"return_code":int} only!"""})
                print("CAPTCHA Identifier Agent Failed to Format. Retrying...")
                continue
            return model_output
        else:
            tool_name = tool_calls[0].function.name
            print("CAPTCHA Identifier Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})

async def solve_captcha(captcha_key, ai_key, session, captcha_type):
    solver = TwoCaptcha(captcha_key)
    path_to_captcha = "error_handling/CAPTCHA.jpg"
    if captcha_type == 1:
        result = solver.normal(path_to_captcha) #returns text
    elif captcha_type == 2:
        result = solver.grid(path_to_captcha) #returns numbers of boxes

    client = OpenAI(api_key = ai_key, base_url = "https://openrouter.ai/api/v1")
        
    messages = [{"role":"system","content":"""
    #Role
    You are a captcha executor agent.

    #OBJECTIVE:
    Given the correct answer to the captcha, you are to solve the captcha challenge displayed on the user's screen.

    #Workflow:
    1. Examine the user's browser, and the captcha solution given to you.
    2. Interact with the captcha challenge using the solution given. For a normal captcha (scrambled/messy text), a string of the text will be given as the solution. For grid captcha (requires selection of boxes in a grid), numbers representing the boxes to select will be given to you.
    3. Inspect browser to see if captcha is successful, and give the corresponding return code.

    #RETRUN CODES:
    - 0: CAPTCHA solved successfully
    - 1: CAPTCHA solve failed

    #OUTPUT:
    Return ONLY a valid JSON object:
    {"return code":int}
    **Do not provide commentary or explanations.**
"""},
    {"role":"user","content":result}]
    tools_available = format_tools_advertisement((await session.list_tools()).tools)
    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
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
                model_output = int(json.loads(chat.choices[0].message.content).get("return code"))
            except:
                messages.append({"role":"user","content":"""Output must be in JSON format of {"return_code":int} only!"""})
                print("CAPTCHA Solver Agent Failed to Format. Retrying...")
                continue

            return model_output
        else:
            tool_name = tool_calls[0].function.name
            print("CAPTCHA Solver Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})
