#environment variable names are tavilyAPIkey and openRouterAPIkey

import sys
sys.path.append("C:\\Users\\User\\WebSlave\\response")
sys.path.append("C:\\Users\\User\\WebSlave\\interface")
import asyncio

import os
from response.response_agent import respond_to_survey
from interface.browser_connection import browser_session
from interface.interface_agent import extract_question, submit_answer
from error_handling.premature_submission import handle_premature_submission

async def main():
    api_key = os.getenv("openRouterAPIkey")
    async with browser_session() as session:
        survey_status = None
        exception_counter = 0
        while True:
            if exception_counter > 10:
                return
            try:
                question = await extract_question(api_key, session)
            except:
                exception_counter+=1
                continue
            try:
                answer = respond_to_survey(str(question), api_key)
            except:
                exception_counter+=1
                continue
            try:
                submission_code = int(await submit_answer(answer, session, api_key))
            except:
                exception_counter+=1
                continue
            if submission_code == 0:
                continue
            elif submission_code == 2:
                break
            elif submission_code == 1:
                exception_counter+=1
                await handle_premature_submission(api_key, session, profile_updated=True)
                continue
        print("Survey Complete!")
        

if __name__ == "__main__":
    asyncio.run(main())
