# ClearSwarm

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular and extensible multi-agent system built in Python that interfaces with LLM models through OpenAI-compatible APIs. Agents can call tools and other agents **asynchronously**, enabling parallel execution with execution tracking in SQLite. Synchronous operation is also possible.

A short demo of a swarm solving mathematical calculations.
[https://github.com/user-attachments/assets/a81c7233-86dc-420b-94fa-48b7175bbbf3](https://github.com/user-attachments/assets/a81c7233-86dc-420b-94fa-48b7175bbbf3)

## Features

- **Modular Agent Architecture** - Dynamic agent loading from configuration directories
- **Async Parallel Execution** - Multiple sub-agents and tools run concurrently
- **XML-Based Tool Calling** - Clean, parseable format for tool invocations
- **Full Execution Tracking** - SQLite database logs all agent and tool executions
- **Web Interface** - Real-time monitoring with WebSocket updates and interactive graph visualization
- **Customizable Prompts** - YAML-based prompt configuration with multi-language support

## Requirements

- Python 3.8+
- Access to an OpenAI-compatible API

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure `.env` file with your API credentials:
```bash
cp .env.example .env
# Edit .env with your settings
```

```
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4
```

## Usage

### Web Interface (GUI)

The system includes a graphical web interface for agent management:

```bash
# Start web interface (from project root)
./start_web.sh
```

Then open in browser: [http://localhost:8000](http://localhost:8000)

> ⚠️ **SECURITY WARNING**
> This application has been coded by using AI agents. The author put all possible effort to make it as safe as possible, but is aware of missing parts and vulnerabilities. The application does not create danger as is, but has a potential to introduce danger if it gets extended with tools that are not prepared to be safe. At this stage the application allows to organize simple interactions between agents based purely on their answers.
>
> The web interface has **no authentication** and provides full access to agent execution, including the ability to run arbitrary tools. By default, it binds to `127.0.0.1` (localhost only) for security reasons.
>
> **DO NOT** expose this application to the network or internet without implementing proper authentication and HTTPS. If you need remote access, use a secure tunnel (e.g., SSH port forwarding) or set up a reverse proxy with authentication.
>
> To explicitly bind to all interfaces (at your own risk):
> ```bash
> HOST=0.0.0.0 ./start_web.sh
> ```

**Web interface features:**
- Launch agents via form
- Real-time execution monitoring (WebSocket)
- Agent and tool call tree visualization
- Detailed execution information
- JSON log download
- Auto-refresh execution list
- Modern dark theme interface

See [web_interface/README.md](src/multi_agent/web_interface/README.md) for full documentation.

### CLI (Command Line Interface)

#### Run an agent

```bash
python -m multi_agent <agent_name> "<message>"
```

Example:
```bash
python -m multi_agent coordinator "Calculate 15 + 27"
```

#### List available agents

```bash
python -m multi_agent --list-agents
```

#### List available tools

```bash
python -m multi_agent --list-tools
```

#### Show execution history

```bash
python -m multi_agent --show-history
```

### Prompt Configuration

The system supports full customization of all system prompts, messages, and errors:

```bash
# Use default prompts (user/prompts/default.yaml)
python -m multi_agent coordinator "Calculate 15 + 27"

# Use custom prompt file
python -m multi_agent coordinator "Calculate 15 + 27" --prompts-file custom.yaml
```

**Creating custom prompts:**

1. Copy `user/prompts/default.yaml` as a template
2. Edit the desired text - the system uses fallback for missing values
3. Prompts support variable substitution: `{agent_name}`, `{task_id}`, etc.

Example customization (`user/prompts/custom.yaml`):
```yaml
log_messages:
  agent_start: "Starting agent: {agent_name} (ID: {agent_id})"
  agent_completed: "Agent completed after {iterations} iterations"
```

See `user/prompts/default.yaml` for the full list of configurable prompts.

### Execution Graph Visualization

The web interface includes an interactive graph visualization feature. Click "View Tree" on any execution to see:
- Real-time agent hierarchy as a network graph
- Color-coded node states (running, completed)
- Sync vs async connection types
- Interactive zoom, pan, and node dragging

See [GRAPH_VISUALIZATION.md](GRAPH_VISUALIZATION.md) for details.

## Example Tasks

### Examples

**Simple task:**
```bash
python -m multi_agent math_assistant "Calculate 25 + 17, then multiply by 2, then subtract 10"
```

**Complex research:**
```bash
python -m multi_agent researcher "Analyze Q1=15000, Q2=18000, Q3=21000. Calculate total and average."
```

**Coordinator task:**
```bash
python -m multi_agent coordinator "Calculate revenues Jan=12000, Feb=15000, Mar=18000. Find average and growth rate."
```

## Project Structure

```
.
├── src/multi_agent/        # Main package
│   ├── core/               # Core framework
│   │   ├── agent.py        # Agent implementation
│   │   ├── orchestrator.py # Task orchestration
│   │   ├── database.py     # SQLite tracking
│   │   ├── llm_client.py   # LLM API client
│   │   ├── prompts.py      # Configurable prompts
│   │   └── config.py       # Environment config
│   ├── tools/              # Tool system
│   └── web_interface/      # FastAPI web UI
├── user/                   # User-configurable content
│   ├── agents/             # Agent configurations
│   ├── tools/              # Custom tools
│   └── prompts/            # Prompt templates (YAML)
├── tests/                  # Test suite
├── logs/                   # Execution logs (auto-generated)
└── output/                 # File output directory
```

## Creating Custom Agents

1. Create a directory in `user/agents/` with your agent name
2. Add three required files:
   - `description.txt` - Description for other agents
   - `system_prompt.txt` - Agent's system prompt
   - `tools.txt` - List of tools/agents (one per line)

Example:
```bash
mkdir user/agents/my_agent
echo "My agent description" > user/agents/my_agent/description.txt
echo "You are a helpful assistant..." > user/agents/my_agent/system_prompt.txt
echo "calculator" > user/agents/my_agent/tools.txt
```

## Creating Custom Tools

1. Create a file in `user/tools/` inheriting from `BaseTool`
2. Implement required methods: `name`, `description`, `execute`

Example:
```python
from multi_agent.tools.base import BaseTool

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Tool description"

    def execute(self, param: str) -> str:
        return f"Result: {param}"
```

## How It Works

1. Agent is initialized with configuration from its directory
2. Agent receives a user message
3. Agent can invoke tools or other agents using XML format:
```xml
<tool_call>
<tool_name>tool_name</tool_name>
<parameters>
{"param": "value"}
</parameters>
</tool_call>
```
4. Multiple tool calls in a single response execute **in parallel**
5. Results are returned to the agent's context
6. All executions are tracked in the SQLite database

## Logging

The system automatically logs all LLM interactions to `./logs/`.

Each agent execution creates `agent_{agent_id}.json` containing:
- Full message history (request)
- LLM responses (response)
- Token usage statistics
- Timestamps for all calls
- Tool and sub-agent call information

## Database

The system automatically tracks all agent executions in `agents.db`:
- Agent ID
- Agent name
- Parent agent ID and name
- Start and completion timestamps
- Current execution state

## Development

### Running Tests

```bash
# Install dev dependencies first
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output and coverage
pytest tests/ -v --cov=multi_agent
```

Test configuration is defined in `pyproject.toml` with async support and coverage enabled by default.

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linters
flake8 src/ tests/
mypy src/
```

### Using Makefile

```bash
make install      # Install dependencies
make install-dev  # Install dev dependencies
make test         # Run tests
make lint         # Run linters
make format       # Format code
make clean        # Clean build artifacts
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
