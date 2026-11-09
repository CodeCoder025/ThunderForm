#environment variable names are captchaAPIkey and openRouterAPIkey

import sys
sys.path.append("C:\\Users\\User\\ThunderForm\\response")
sys.path.append("C:\\Users\\User\\ThunderForm\\interface")
import asyncio
import json

import os
from response.response_agent import respond_to_survey
from interface.browser_connection import browser_session
from interface.interface_agent import extract_question, submit_answer
from error_handling.premature_submission import handle_premature_submission
from error_handling.CAPTCHA_solve import identify_captcha, solve_captcha_auto

async def main():
    ai_api_key = os.getenv("openRouterAPIkey")
    captcha_api_key = os.getenv("captchaAPIkey")
    print("OpenRouter key loaded:", bool(ai_api_key))
    print("2Captcha key loaded:", bool(captcha_api_key))
    
    async with browser_session() as session:
        survey_status = None
        exception_counter = 0
        while True:
            if exception_counter > 10:
                return

            captcha_code = await identify_captcha(ai_api_key, session)

            if captcha_code != 0:
                captcha_success_code = await solve_captcha_auto(captcha_api_key, ai_api_key, session, captcha_code)
                if captcha_success_code == 1:
                    captcha_success_code = await solve_captcha_auto(captcha_api_key, ai_api_key, session, captcha_code)
                    if captcha_success_code == 1:
                        continue #Since captcha solving is expensive ill only reactivate the loop once the solver fails twice
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
