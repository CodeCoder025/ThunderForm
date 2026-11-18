from openai import OpenAI
from openrouter import OpenRouter
import os
import json
from pydantic import BaseModel, Field, ConfigDict

from browser_connection import execute_tool, format_tools_advertisement, format_tool_output
from typing import Literal

class AnswerSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    return_code : Literal[0,1,2] = Field(
        description="0 = answer successfully filled in; 1 = unable to fill in; 2 = entire survey completed and submitted, with no other pages to navigate to"
    )
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
    6. Exit and output the return code.

    ## Critical Rules
    - NEVER navigate while unanswered questions remain.
    - NEVER submit the survey prematurely.
    - Do not modify previously submitted answers.

    ## Submission Codes
    - 0: Successfully filled in, and if required, navigated to the next page.
    - 1: Unable to fill in.
    - 2: Entire survey completed and submitted, with no further pages to navigate to.
    You are to infer, based on context and DOM of the webpage, when to return with code 2. For example, if the next navigational button available is a "submit" button or "finish" button instead of a "proceed" button, you can click it an return code 2.

    ## Output Format
    Do not return anything to the user in the form of a message. To return the submission code, use the return_state tool.
    """}]

    schema = AnswerSubmission.model_json_schema()

    if answer == "Abort":
        messages.append({"role":"system","content":"User has no answer to submit. Navigate to the next section of the survey."})
    else:
        messages.append({"role":"user","content":answer})

    tools = format_tools_advertisement((await session.list_tools()).tools)
    tools.append({"type":"function",
                  "function":{
                      "name":"return_state",
                      "description":"Returns the submission code to the user. 0 = successfully filled in; 1 = unable to fill in; 2 = entire page filled in, with no further pages of questions to navigate to.",
                      "parameters":schema
                  }})

    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=tools,
            tool_choice="required"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if not tool_calls or len(tool_calls) == 0:
            print("Answer Submission Agent Failed to Return with Tool Call!")
            messages.append({"role":"system","content":"Return the submission status code using the tool return_state. Do not return a message directly to the user!"})
            continue
        else:
            tool_name = tool_calls[0].function.name
            print("Answer Submission (Interface) Agent Called Tool: %s"%tool_name)
            arguments = json.loads(tool_calls[0].function.arguments)
                        
            if tool_name == "return_state":
                return arguments["return_code"]
            
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})

class ExtractQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question : None | str = Field(
        description="The text of the first unanswered question in the survey currently displayed in the user's browser. If no unanswered question can be identified, return None"
    )
    type: Literal["multiple choice", "free response"] = Field(
        description = "The type of the question identified"
    )
    options: None | list[str] = Field(
        description= "None for free response questions. Answer options of a multiple choice question."
    )

async def extract_question(api_key, session):
    client = OpenAI(api_key = api_key, base_url = "https://openrouter.ai/api/v1")
    
    messages = [{"role":"system","content":"""
    #Role
    You are an interface inspection agent.

    #OBJECTIVE:
    Identify the **first unanswered question** in the survey currently
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
    Do not return a message to the user. Return the question via the return_question tool, never through a message!
"""}, {"role":"user","content":"Begin. Inspect the page and return the first unanswered question via return_question. "}]

    schema = ExtractQuestionResponse.model_json_schema()
    tools = format_tools_advertisement((await session.list_tools()).tools)
    tools.append({"type":"function",
                  "function":{
                      "name":"return_question",
                      "description":"returns the extracted question to the user",
                      "parameters":schema
                  }})
    while True:
        chat = client.chat.completions.create(
            model = "deepseek/deepseek-v4-flash",
            messages = messages,
            tools=tools,
            tool_choice="required"
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Interface Agent!")

        tool_calls = chat.choices[0].message.tool_calls
        messages.append(chat.choices[0].message)
        if (not tool_calls or len(tool_calls) == 0):
            print("Question Extractor Agent Did Not Return with Tool Call")
            messages.append({"role":"system","content":"Do not return a message to the user. Return only using the return_question tool!"})
            continue
        else:
            tool_name = tool_calls[0].function.name
            print("Question Extractor (Interface) Agent Called Tool: %s"%tool_name)
            arguments = json.loads(tool_calls[0].function.arguments)
            if tool_name == "return_question":
                return arguments
            output = await execute_tool(session, tool_name, arguments)
            messages.append({"role":"tool","tool_call_id":tool_calls[0].id, "content":output})
