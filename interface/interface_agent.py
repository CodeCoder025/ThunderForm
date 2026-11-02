from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json

from browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def submit_answer(answer, session, api_key): #the answer variable is a list of the question and the answer

    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")

    messages = [{"role":"system","content":"""
    Youre role is to fill in the question with the answer provided.
    Afterwards, if all questions on the page have been filled in, click on the relevant button (e.g. "submit","next", "proceed", arrow symbol button, etc) to proceed to the next page. You can inspect the DOM to understand which button will help you get to the next page.
    Your output MUST be in a JSON format only
    Example:
    {"return code":"0"}
    return code 0 means that the question was sucessfully filled, 1 means that the question cannot be filled (e.g. for multiple choice, answer is not an option), 2 means that the entire survey is complete (i.e. a "submit" or "finish survey" button was clicked. "Next page" or related buttons do not count!)

    Do not add any commentary, explainations or supporting text. Only return the JSON.
    """},
                {"role":"user","content":answer}]

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=format_tools_advertisement((await session.list_tools()).tools),
            tool_choice = "auto"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if not tool_calls or len(tool_calls) == 0:
            output = chat.choices[0].message.content
            try:
                return_code = int(json.loads(output)["return code"])
            except:
                messages.append({"role":"user","content":"""Ouptut must be in JSON format of {"return code":str} only"""})
                print("Answer Submission Agent Failed to Format. Retrying...")
                continue
            return return_code
        else:
            tool_name = tool_calls[0].function.name
            print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})

async def extract_question(api_key, session):
    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    Your task is to identify the first unanswered question in the survey on the browser of the user.
    After inspecting the browser, you MUST return a JSON array.
    Example:
    [{
    "question":"Do you speak English?",
    "type":"multiple choice",
    "options":["Yes","No"]}]
    Do not provide explainations, commentary, or introductory text.
    Questions are either "multiple choice" or "free response".
    """}]

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools=format_tools_advertisement((await session.list_tools()).tools),
            tool_choice="auto"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            try:
                model_output = json.loads(chat.choices[0].message.content)
            except:
                messages.append({"role":"user","content":"""Output must be in JSON format of {"question":str, "type":str,"options": list or null} only!"""})
                print("Question Extractor Agent Failed to Format. Retrying...")
                continue
            return model_output
        else:
            tool_name = tool_calls[0].function.name
            print("Question Extractor (Interface) Agent Called Tool: %s"%tool_name)
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})
