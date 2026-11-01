#environment variable names are tavilyAPIkey and openRouterAPIkey
#Everythin in main.py happens in functions, which are defined in other files

import sys
sys.path.append("C:\\Users\\User\\WebSlave\\response")
sys.path.append("C:\\Users\\User\\WebSlave\\interface")
import asyncio

import os
from response.response_agent import respond_to_survey
from interface.browser_connection import browser_session
from interface.interface_agent import extract_question, submit_answer

async def main():
    api_key = os.getenv("openRouterAPIkey")
    async with browser_session() as session:
        survey_status = None
        while True:
            question = await extract_question(api_key, session)
            answer = respond_to_survey(str(question), api_key)
            submission_code = int(await submit_answer(answer, session, api_key))
            if submission_code == 0:
                continue
            elif submission_code == 2:
                break
            elif submission_code == 1:
                raise Exception("%s is an invalid answer to %s"%(answer, question))
        print("Survey Complete!")
        

if __name__ == "__main__":
    asyncio.run(main())
