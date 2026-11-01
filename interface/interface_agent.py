from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json

from browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def submit_answer(answer, session, api_key): #the answer variable is a list of the question and the answer

    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")

    messages = [{"role":"system","content":"""
    You are a browser agent helping the user complete a survey.
    Your role is to facilitate the input of responses given to you, into the survey questionaire itself, which is open on the browser of the person.
    You have access to an MCP browser connection.
    You will be given the question and the answer in the form of [question, answer], and your job is to use MCP tools to input the given answer into its corresponding field. 
    After filling in the answer to the question, you are to then carry out a suitable interaction to proceed to the next question or submit the survey response (e.g. scroll down, "submit", "next" button, etc).
    If answer is submitted smoothly, return 0. (for multiple choice questions) if answer is not one of the options, return 1. If survey is complete, return 2. Do not return anything else
    """},
                {"role":"user","content":answer}]

    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=format_tools_advertisement((await session.list_tools()).tools),
            tool_choice = "auto"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")
        messages.append(chat.choices[0].message)

        tool_calls = chat.choices[0].message.tool_calls
        if not tool_calls or len(tool_calls) == 0:
            return chat.choices[0].message.content
        else:
            tool_name = tool_calls.function.name
            arguments = ast.literal_eval(tool_calls.function.arguments)
            try:
                output = execute_tool(session, tool_name, arguments)
            except:
                output = execute_tool(session, tool_name, str(arguments))

            try:
                messages.append({"role":"assistant","tool_call_id":tool_calls.id, "content":format_tool_output(output)})
            except:
                messages.append({"role":"assistant","tool_call_id":tool_calls.id, "content":str(output)})

async def extract_question(api_key, session):
    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    You are a browser agent helping to extract the question of a survey on the user's browser.
    You are to return the question and options exactly in the form of a list, and nothing else. The list should take the form as below --> [question, [option1, option2, ...]] in the event of a multiple-choice question and [question, None] in the event of a free-response question.
    Only extract one question. The question to extract is the question directly after the last question which has already been filled out (i.e. the first question which has yet to be filled out)
    You have access to an MCP browser connection.
    """}]

    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=format_tools_advertisement((await session.list_tools()).tools)
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")
        messages.append(chat.choices[0].message)

        tool_calls = chat.choices[0].message.tool_calls
        if not tool_calls or len(tool_calls) == 0:
            model_output = chat.choices[0].message.content
            if model_output[1] == None or model_output[1] == []:
                question_extracted = {"question":model_output[0],
                                    "type":"Free-response",
                                    "options":None}
            else:
                question_extracted = {"question":model_output[0],
                                                    "type":"Multiple-choice",
                                                    "options":model_output[1]}

            return question_extracted
        else:
            tool_name = tool_calls[0].function.name
            arguments = ast.literal_eval(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"assistant","tool_call_id":tool_calls[0].id, "content":output})
