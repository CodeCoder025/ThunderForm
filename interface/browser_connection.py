from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import asyncio

@asynccontextmanager
async def browser_session():
    server = StdioServerParameters(
        command = "npx",
        args= ["-y","@browsermcp/mcp@latest"],
        env = None
    )

    async with stdio_client(server) as (read,write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            try:
                yield session
            finally:
                pass

def format_tools_advertisement(mcp_tools):
    formatted_tools = []

    for tool in mcp_tools:
        formatted_tools.append({"type":"function",
                                "function":{
                                    "name":tool.name,
                                    "description":tool.description or "",
                                    "parameters": tool.inputSchema
                                }})
        return formatted_tools

def format_tool_output(output):
    parts = []
    for item in output.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))

    formatted_output = "\n".join(parts)

    if output.isError:
        return "Tool Execution Error: %s"%output

    if formatted_output:
        return formatted_output
    else:
        return "No Textual Output Returned"

async def execute_tool(session, name, arguments):
    result = await session.call_tool(name, arguments)
    return format_tool_output(result)
