#environment variable names are captchaAPIkey and openRouterAPIkey

import sys
sys.path.append("C:\\Users\\User\\WebSlave\\response")
sys.path.append("C:\\Users\\User\\WebSlave\\interface")
import asyncio

import os
from response.response_agent import respond_to_survey
from interface.browser_connection import browser_session
from interface.interface_agent import extract_question, submit_answer
from error_handling.premature_submission import handle_premature_submission
from error_handling.CAPTCHA_solve import identify_captcha, solve_captcha

async def main():
    ai_api_key = os.getenv("openRouterAPIkey")
    async with browser_session() as session:
        survey_status = None
        exception_counter = 0
        while True:
            if exception_counter > 10:
                return

            captcha_code = identify_captcha()
            if captcha_code:
                solve_captcha(captcha_code)
            
            try:
                question = await extract_question(ai_api_key, session)
            except:
                exception_counter+=1
                continue
            try:
                answer = respond_to_survey(str(question), ai_api_key)
            except:
                exception_counter+=1
                continue
            try:
                submission_code = int(await submit_answer(answer, session, ai_api_key))
            except:
                exception_counter+=1
                continue
            if submission_code == 0:
                continue
            elif submission_code == 2:
                break
            elif submission_code == 1:
                exception_counter+=1
                await handle_premature_submission(ai_api_key, session, profile_updated=True)
                continue
        print("Survey Complete!")
        

if __name__ == "__main__":
    asyncio.run(main())
