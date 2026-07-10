# OpenManus-Lite

A minimal, faithful re-implementation of the [OpenManus](https://github.com/FoundationAgents/OpenManus) general-purpose AI agent framework. Built as a learning/reference project after studying the original codebase.

OpenManus-Lite keeps the same core architecture — a step-based agent loop that calls an LLM with a tool collection until the task is done — but in a compact, readable form.

## Architecture

```
main.py
  └─ Manus (ToolCallAgent → ReActAgent → BaseAgent)
        ├─ think():  LLM.ask_tool(messages, tools)  → decide tool calls
        ├─ act():    ToolCollection.execute(tool)   → run the tool
        └─ loop:     step() = think() → act()  until FINISHED / max_steps

app/
  agent/   base, react, toolcall, manus
  tool/    python_execute, bash, str_replace_editor, ask_human, terminate, create_chat_completion
  llm.py   OpenAI-compatible async chat + tool calling wrapper
  schema.py  Message / Memory / ToolCall / AgentState
  config.py  TOML config loader
```

## Features

- **Step-based agent loop** with memory, state machine, and stuck-detection.
- **Tool calling** via an OpenAI-compatible API.
- **Bundled tools**: `python_execute`, `bash`, `str_replace_editor`, `ask_human`, `terminate`, `create_chat_completion`.
- **Pydantic-based** schemas and tool definitions.
- **Configurable** LLM via `config/config.toml`.

## Install

```bash
pip install -r requirements.txt
cp config/config.example.toml config/config.toml
# edit config.toml with your API key / base_url / model
```

## Run

```bash
python main.py
# then type your task, e.g.:
# "Write a Python script that prints the first 10 Fibonacci numbers, run it, and save the output to workspace/fib.txt"
```

## How it works

1. `Manus.run(prompt)` stores the user request in memory and enters the RUNNING state.
2. Each step calls `think()` which asks the LLM (with the tool schemas) what to do next.
3. `act()` executes the chosen tools and feeds the observations back into memory.
4. When the model calls `terminate`, the agent reports the final result and stops.

## Differences from OpenManus

| OpenManus | OpenManus-Lite |
|-----------|----------------|
| Browser-use, MCP, sandbox, multi-agent flow | Core loop + local code/shell/file tools (no browser/MCP) |
| Full token accounting | minimal |
| Docker/Daytona sandbox | optional config stub |

This is a learning scaffold — it demonstrates the exact think→act loop that powers the original, without the heavier integrations.

## License

MIT
