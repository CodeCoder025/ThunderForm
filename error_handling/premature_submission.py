#Undo all fields in this page and restart form filling logic from the extractor agent.
from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import json
from response.profile_manager import update_profile
from interface.browser_connection import execute_tool, format_tools_advertisement, format_tool_output

async def handle_premature_submission(api_key, session, profile_updated = False):
    print("Premature Submission Occurred. Handling...")

    if profile_updated == True:
        update_profile(None, api_key, message_override=True) #erases information previously added to profile (in case error comes in the response being invalid)

    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    Undo all fields in the current page of the form on the browser of the user. You are only allowed to scroll up and down to navigate. Do not press any navigational buttons to navigate out of the current form page.
    """}]

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
            return
        else:
            tool_name = tool_calls[0].function.name
            print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
            arguments = json.loads(tool_calls[0].function.arguments)
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})