#environment variable names are tavilyAPIkey and openRouterAPIkey
#Everythin in main.py happens in functions, which are defined in other files

import sys
sys.path.append("C:\\Users\\User\\WebSlave\\response")
sys.path.append("C:\\Users\\User\\WebSlave\\interface")

import os
from response.response_agent import respond_to_survey

api_key = os.getenv("openRouterAPIkey")

def main():
    survey_status = None
    while survey_status != "complete":
        pass

if __name__ == "__main__":
    main()
