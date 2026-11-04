from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json

from browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def submit_answer(answer, session, api_key): #the answer variable is a list of the question and the answer

    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")

    messages = [{"role":"system","content":"""
    # Role
    You are a survey answer submission agent.

    # Objective
    Fill in the field of the given question with the answer provided.

    ## Workflow
    1. Inspect the current page.
    2. Identify the relevant question.
    3. Fill in the answer.
    4. Check whether other questions remain unanswered.
    5. Only navigate when the page is complete.

    ## Critical Rules
    - NEVER navigate while unanswered questions remain.
    - NEVER submit the survey prematurely.
    - Do not modify previously submitted answers.

    ## Return Codes
    - 0: Successfully filled in.
    - 1: Unable to fill in.
    - 2: Entire survey completed and submitted.

    ## Output Format
    Return ONLY valid JSON:

    ```json
    {"return code":"0"}
    """},
                {"role":"user","content":answer}]

    if answer == "Abort":
        messages = [{"role":"system","content":"Navigate to the next section of the survey."}]

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
                return 1

        else:
            tool_name = tool_calls[0].function.name
            print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
            arguments = json.loads(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})

async def extract_question(api_key, session):
    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    #Role
    You are an interface inspection agent.

    #OBJECTIVE:
    Identify the first unanswered question in the survey currently
    displayed in the user's browser.

    #INSTRUCTIONS:
    1. Inspect the currently visible browser page.
    2. Identify the questions and their answer fields.
    3. Determine whether each question has already been answered.
    4. If the first unanswered question is visible, return it immediately.
    5. Only scroll if no unanswered question is visible.
    6. Do not repeatedly inspect the same page or element.
    7. Do not interact with answer fields or submit any answers.
    8. If you cannot identify an unanswered question, return null.

    #OUTPUT:
    Return ONLY a valid JSON object:

    {
        "question": "Question text",
        "type": "multiple choice",
        "options": ["Option 1", "Option 2"]
    }

    For free response questions, use:
    {
        "question": "Question text",
        "type": "free response",
        "options": null
    }

    If no unanswered question can be identified, return:
    null

    **Do not provide commentary or explanations.**
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
