# WebSlave

WebSlave is an **autonomous survey completion and form filling agent** which helsp users fill up long, tedious forms with minimum human intervention. The form is filled using information provided by the user in the _my_profile.txt_ file (under the _response_ folder), or hypothetically synthesised by the agent.

## Workflow

The interface agent, using the Browser MCP Connection, interacts with the browser and extracts the question.
It sends the question to the response agent, which reads _my_profile.txt_ to determine if information to address the question is available. If otherwise, it synthesises a response and writes it into _my_profile.txt_.
The reponse agent then sends the question, along with the answer, back to the interface agent, which inputs the answer into the form or survey.
This would repeat until the survey is complete, determined by the interface agent.

### Yet to Do:

- increase robustness of suitable CAPTCHA challenges, to include drag and drop captcha, etc (solver bot should be given different message based on CAPTCHA type detected, rather than being given one massive prompt with instructions for every captcha type)
- completing multiple surveys in a single run (can navigate between a survey selection menu, or between captcha completion and survey start. This would essentially be the orchestrator agent)
- option to disable synthesis of hypothetical responses
- nice, clean user interface
- AI token usage efficiency (send all questions then receive all answers and fill one by one, rather than doing the entire workflow N times)

### Dependencies

2Captcha, Pillow, BrowserMCP, OpenRouter, OpenAI are necessary for this script to run as intended. An OpenRouter API key with access to Deepseek V4 Flash will be necessary. As this is a premium model, credits will be needed (user can expect a cost of less than one cent per five questions, though subject to question complexity)

### Risks

Please note that this software gives the agent control over your browser. By running any code in this project, you accept and are willing to bear the risks associated with this agentic control.

### Violation of Terms of Use

Many survey or form-hosting software prohibit the use of agents or autonomous algorithms to fill in surveys. Please ensure that the use of WebSlave does not violate the terms of use of any third-party software. This tool is built to be used in good faith, as well as for learning purposes ONLY.
