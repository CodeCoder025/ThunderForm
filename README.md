# WebSlave

WebSlave is an **autonomous survey completion and form filling agent** which helsp users fill up long, tedious forms with minimum human intervention. The form is filled using information provided by the user in the _my_profile.txt_ file (under the _response_ folder), or hypothetically synthesised by the agent.

## Workflow

The interface agent, using the Browser MCP Connection, interacts with the browser and extracts the question.
It sends the question to the response agent, which reads _my_profile.txt_ to determine if information to address the question is available. If otherwise, it synthesises a response and writes it into _my_profile.txt_.
The reponse agent then sends the question, along with the answer, back to the interface agent, which inputs the answer into the form or survey.
This would repeat until the survey is complete, determined by the interface agent.

### Yet to Do:

- survey logger (what surveys have been completed, how many API tokens it took, payout if any, etc)
- option to disable synthesis of hypothetical responses
- nice, clean user interface
- completing multiple surveys in a single run (can navigate between a survey selection menu)
- AI token usage efficiency (send all questions then receive all answers and fill one by one, rather than doing the entire workflow N times)

### Dependencies

BrowserMCP, OpenRouter, OpenAI are necessary for this script to run as intended. An OpenRouter API key with access to Deepseek V4 Flash will be necessary. As this is a premium model, credits will be needed (user can expect a cost of less than one cent per five questions, though subject to question complexity)

### Risks

Please note that this software gives the agent control over your browser. By running any code in this project, you accept and are willing to bear the risks associated with this agentic control.

### Violation of Terms of Use

Many survey or form-hosting software prohibit the use of agents or autonomous algorithms to fill in surveys. Please ensure that the use of WebSlave does not violate the terms of use of any third-party software. This tool is built to be used in good faith.

### Last Error Message

(.venv) PS C:\Users\User\WebSlave> & c:\Users\User\WebSlave\.venv\Scripts\python.exe c:/Users/User/WebSlave/main.py

- Exception Group Traceback (most recent call last):
  | File "c:\Users\User\WebSlave\main.py", line 32, in <module>
  | asyncio.run(main())
  | File "C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\asyncio\runners.py", line 190, in run
  | return runner.run(main)
  | ^^^^^^^^^^^^^^^^
  | File "C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\asyncio\runners.py", line 118, in run
  | return self.\_loop.run_until_complete(task)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  | File "C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\asyncio\base_events.py", line 650, in run_until_complete
  | return future.result()
  | ^^^^^^^^^^^^^^^
  | File "c:\Users\User\WebSlave\main.py", line 16, in main
  | async with browser_session() as session:
  | File "C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\contextlib.py", line 222, in **aexit**
  | await self.gen.athrow(typ, value, traceback)
  | File "c:\Users\User\WebSlave\interface\browser_connection.py", line 15, in browser_session
  | async with stdio_client(server) as (read,write):
  | File "C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\contextlib.py", line 222, in **aexit**
  | await self.gen.athrow(typ, value, traceback)
  | File "C:\Users\User\WebSlave\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  | async with anyio.create_task_group() as tg:
  | File "C:\Users\User\WebSlave\.venv\Lib\site-packages\anyio_backends_asyncio.py", line 847, in **aexit**
  | raise BaseExceptionGroup(
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
  | Exception Group Traceback (most recent call last):
  | File "C:\Users\User\WebSlave\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
  | yield read_stream, write_stream
  | File "c:\Users\User\WebSlave\interface\browser_connection.py", line 16, in browser_session
  | async with ClientSession(read, write) as session:
  | File "C:\Users\User\WebSlave\.venv\Lib\site-packages\mcp\client\session.py", line 514, in **aexit**
  | result = await self.\_task_group.**aexit**(exc_type, exc_val, exc_tb)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  | File "C:\Users\User\WebSlave\.venv\Lib\site-packages\anyio_backends_asyncio.py", line 847, in **aexit**
  | raise BaseExceptionGroup(
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
  | Traceback (most recent call last):
  | File "c:\Users\User\WebSlave\interface\browser_connection.py", line 20, in browser_session
  | yield session
  | File "c:\Users\User\WebSlave\main.py", line 21, in main
  | submission_code = int(await submit_answer(answer, session, api_key))
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  | ValueError: invalid literal for int() with base 10: 'I\'m ready to help fill in the survey. Please provide me with the **[question, answer]** pair so I can proceed.\n\nFor example:\n- **Question:** "What is your age?" \n- **Answer:** "25"\n\nThen I\'l
