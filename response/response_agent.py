from openai import OpenAI
from openrouter import OpenRouter
import os
import ast
import subprocess

from profile_manager import update_profile

def respond_to_survey(question, api_key=os.getenv("openRouterAPIkey")):

    client = OpenAI(api_key=api_key, base_url= "https://openrouter.ai/api/v1")

    messages = [{"role":"system", "content":"""
    You are a survey response agent.
    You are to answer a question, given in the form of {"question":question, "type":multiple_choice_or_free_response,"options":none_if_free_response}
    A description of your profile can be found in the file response/my_profile.txt.
    Answer the following question based on this profile.
    If there is no information related to the question in the profile description, invent an answer.
    For multiple-choice questions, state your answer exactly as stated in the options. For free response questions, answer the question directly; do not add any unnecessary details into your answer.
    Do not answer in a full sentence, just give the exact relevant detail."""},
                {"role":"user","content":question}]

    while True:
        chat = client.chat.completions.create(
            model="deepseek/deepseek-v4-flash",
            messages = messages,
            tools = [{"type":"function",
                      "function":{
                          "name":"ReadFile",
                          "description":"Read and return contents of a file",
                          "parameters": {
                              "required":["file_path"],
                              "type":"object",
                              "properties": {
                                  "file_path": {
                                      "type":"string",
                                      "description":"path to file to read"
                                  }
                              }
                          }
                      }
            },
            {"type":"function", #bash functions for file discovery
             "function":{
                 "name":"Bash",
                 "description":"run a shell command",
                 "parameters":{
                     "type":"object",
                     "required":["command"],
                     "properties":{
                         "command":{
                             "type":"string",
                             "description":"the bash command to execute"
                         }
                     }
                 }
             }
            }
                         ])
                
        
        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No Response Given by Response Agent!")
        messages.append(chat.choices[0].message)

        tool_calls = chat.choices[0].message.tool_calls

        if tool_calls is None:
            info_given = [question, messages[-1].model_dump().get("content")]
            update_profile(info_given, api_key)
            return str(info_given)
        
        else:
            if tool_calls[0].function.name == "ReadFile":
                arguments_asstring = tool_calls[0].function.arguments
                arguments= ast.literal_eval(arguments_asstring)
                with open(arguments.get("file_path"), "r") as profile:
                    profile_description = profile.read()

                messages.append({"role":"tool","tool_call_id":tool_calls[0].id,"content":profile_description})

            elif tool_calls[0].function.name == "Bash":
                arguments = ast.literal_eval(tool_calls[0].function.arguments)
                bash_command = arguments.get("command")
                result = subprocess.run(bash_command, shell = True, capture_output=True, text = True)

                if result.returncode == 0:
                    messages.append({"role":"tool","tool_call_id":tool_calls[0].id,"content":result.stdout})
                elif result.returncode == 1:
                    messages.append({"role":"tool","tool_call_id":tool_calls[0].id,"content":result.stderr})

