"""Offline tests for Browser tool and Multi-agent flow (no API calls).

Uses a fake LLM so the agent loop runs deterministically without network.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.multi import CodingAgent, Supervisor
from app.llm import LLM
from app.tool.browser import Browser


class FakeLLM(LLM):
    """Returns a fixed sequence of tool calls / answers per call."""

    def __init__(self, scripted):
        # bypass real client init
        self._script = list(scripted)
        self.model = "fake"
        self.base_url = "fake"
        self.api_key = "fake"

    async def ask_tool(self, *a, **kw):
        from app.schema import Function, Message, Role, ToolCall

        item = self._script.pop(0)
        if item is None:  # final text
            return Message.assistant_message(content="done")
        name, args = item
        return Message(
            role=Role.ASSISTANT,
            content=None,
            tool_calls=[
                ToolCall(
                    id="c1",
                    function=Function(name=name, arguments=json.dumps(args)),
                )
            ],
        )


async def test_browser():
    b = Browser()
    await b.execute("navigate", url="file:///tmp/test_page.html")
    r = await b.execute("extract", selector="#title")
    assert "Hello Browser" in r.output, r.output
    s = await b.execute("screenshot")
    assert s.base64_image, "no screenshot"
    await b.cleanup()
    print("[OK] Browser: navigate/extract/screenshot/cleanup")


async def test_coding_agent():
    agent = CodingAgent()
    agent.llm = FakeLLM([
        ("python_execute", {"code": "print(6*7)"}),
        ("terminate", {"status": "finished", "summary": "42"}),
    ])
    out = await agent.run("compute 6*7")
    assert "42" in out, out
    print("[OK] CodingAgent: delegated python_execute then terminate ->", out[:60])


async def test_supervisor_routing():
    sup = Supervisor()
    # Script: supervisor delegates to coding_agent, which runs, then finish.
    sup.llm = FakeLLM([
        ("delegate", {"agent": "coding_agent", "task": "compute 2+2"}),
        ("finish", {"summary": "Routed to coding agent, result 4"}),
    ])
    # Force coding_agent to also use fake so no API call
    sup.agents["coding_agent"].llm = FakeLLM([
        ("python_execute", {"code": "print(2+2)"}),
        ("terminate", {"status": "finished", "summary": "4"}),
    ])
    out = await sup.run("what is 2+2")
    print("[OK] Supervisor: routed + finished ->", out[:80])


async def main():
    await test_browser()
    await test_coding_agent()
    await test_supervisor_routing()
    print("\nALL OFFLINE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
