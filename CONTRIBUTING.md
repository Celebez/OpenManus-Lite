# Contributing to OpenManus-Lite

Thanks for your interest in improving OpenManus-Lite! This is a small learning
scaffold, so contributions that keep it **readable and minimal** are preferred.

## How to contribute

1. Fork the repository and create a branch:
   ```bash
   git checkout -b my-change
   ```
2. Set up the environment:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp config/config.example.toml config/config.toml   # add your API key
   ```
3. Make your change. Keep modules small and well-documented.
4. Verify the agent still runs end-to-end:
   ```bash
   python main.py
   # e.g. "Print the first 5 squares and save them to workspace/out.txt"
   ```
5. Commit with a clear message and open a Pull Request.

## Adding a tool

Create `app/tool/your_tool.py` subclassing `BaseTool`, then register it in
`app/agent/manus.py`'s `ToolCollection`. See the existing tools for the pattern.

## Guidelines

- Follow the existing code style (typing + docstrings).
- Do not commit `config/config.toml` (it holds your API key — gitignored).
- Keep the framework minimal; heavy integrations belong in a fork.

## Reporting issues

Open an issue describing the expected vs. actual behavior, plus the steps to
reproduce.
