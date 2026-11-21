# ThunderForm

ThunderForm is an **autonomous survey completion and form filling agent** which helsp users fill up long, tedious forms with minimum human intervention. The form is filled using information provided by the user in the _my_profile.txt_ file (under the _response_ folder), or hypothetically synthesised by the agent.

## Setup

**Please read section on "Terms of Use" before using!**

To install dependencies, run the following:
`pip install 2captcha-python pillow openrouter openai pydantic`

Then, install the BrowserMCP Chrome Extension to allow the script to access your browser. You can download this at https://chromewebstore.google.com/detail/browser-mcp-let-ai-use-yo/bjfgambnhccakkhmkepdoekmckoijdlc

2Captcha and OpenRouter, both of which need API keys, are used in ThunderForm. Configure them and store them as system environment variables:

```
[Environment]::SetEnvironmentVariable("openRouterAPIkey", "your_openrouter_API_key", "User")
[Environment]::SetEnvironmentVariable("captchaAPIkey", "your_2captcha_api_key","User")
```

Replace the placeholders with actual values of your API keys. Though not recommended, you could also hardcode these keys into the script directly for a quick setup.

**Important**: Restart your terminal or IDE after installing these variables. A successful environment variable load will be confirmed by a print statement after the script runs.

To use, simply open the link of the survey in a tab in your browser, and run the _main.py_ script. Customize your profile in _my_profile.txt_, or simply leave it blank for a hypothetical profile!

## Workflow

The interface agent, using the Browser MCP Connection, interacts with the browser and extracts the question.
It sends the question to the response agent, which reads _my_profile.txt_ to determine if information to address the question is available. If otherwise, it synthesises a response and writes it into _my_profile.txt_.
The reponse agent then sends the question, along with the answer, back to the interface agent, which inputs the answer into the form or survey.
This would repeat until the survey is complete, determined by the interface agent.

### Risks

Please note that this software gives the agent control over your browser. By running any code in this project, you accept and are willing to bear the risks associated with this agentic control.

### Terms of Use

Many survey or form-hosting software prohibit the use of agents or autonomous algorithms to fill in surveys. ThunderForm should only be used for ethical purposes, intended for and under the knowledge of all parties. Please ensure that the use of ThunderForm does not violate the terms of use of any third-party software. This tool is built to be used in good faith, as well as for learning purposes ONLY. The consequences of any misuse is to be borne by the user themself.

### Future Updates / Bug Fixes

- answer submission agent would sometimes go rogue and submit its own answers without consulting the question extractor and response agents
- completing multiple surveys in a single run (can navigate between a survey selection menu, or between captcha completion and survey start. This would essentially be the orchestrator agent)
- (MASSIVE UPDATE): let agent live on a cloud server or constantly-running VM, and connect it to a Telegram bot. Add feature such that agent can complete form / survey on user's behalf through a link being sent to it through telegram
- option to disable synthesis of hypothetical responses
- AI token usage efficiency (send all questions then receive all answers and fill one by one, rather than doing the entire workflow N times)
