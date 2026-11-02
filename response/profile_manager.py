from openai import OpenAI
from openrouter import OpenRouter
import ast

def update_profile(new_info, api_key):
    client = OpenAI(api_key=api_key, base_url= "https://openrouter.ai/api/v1")

    information_string = new_info[0]+new_info[1]
    
    messages = [{"role":"system", "content":"A description of your profile can be found in the file response/my_profile.txt. You will be given a piece of information, in the form of a question and an answer (e.g. where do you live? America). Check if this information is already saved in the profile, and if it is not, add this new information into the file. "},
                {"role":"user","content":information_string}]

    while True:
        chat = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages = messages,
            tools= [
                {"type":"function",
                 "function":{
                     "name":"ReadFile",
                     "description":"Read and return contents of a file",
                     "parameters":{
                         "required":["file_path"],
                         "type":"object",
                         "properties":{
                             "file_path":{
                                 "type":"string",
                                 "description":"path to file to read"
                             }
                         }
                     }
                 }},
                 {"type":"function",
                  "function":{
                      "name":"AddContentToFile",
                      "description":"Adds text content to the back of the file",
                      "parameters":{
                          "required":["file_path","content_to_append"],
                          "type":"object",
                          "properties":{
                              "file_path":{
                                  "type":"string",
                                  "description":"path of file to add contents to the back of"},
                                "content_to_append":{
                                    "type":"string",
                                    "description":"content to add to the back of the file"
                              }
                          }
                      }
                  }}
                  
            ]
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("No response given by model")

        messages.append(chat.choices[0].message)
        tool_calls = chat.choices[0].message.tool_calls

        if tool_calls == None or len(tool_calls) == 0:
            break
        else:
            tool_calls = tool_calls[0]
            print("Profile Manager Called Tool: %s"%tool_calls.function.name)
            arguments = ast.literal_eval(tool_calls.function.arguments)

            if tool_calls.function.name == "ReadFile":
                with open(arguments.get("file_path"),"r") as myfile:
                    contents = myfile.read()

                messages.append({"role":"tool","tool_call_id":tool_calls.id,"content":contents})
                continue

            elif tool_calls.function.name == "AddContentToFile":
                with open(arguments.get("file_path"), "a") as myfile:
                    myfile.write(" "+arguments.get("content_to_append"))

                messages.append({"role":"tool","tool_call_id":tool_calls.id,"content":"Text appended successfully!"})
                continue



        