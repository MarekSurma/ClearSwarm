# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release preparation
- CONTRIBUTING.md with contribution guidelines
- SECURITY.md with security policy
- GitHub Actions CI/CD workflow

### Changed
- Improved Python 3.8 compatibility for type hints
- Pinned dependency versions for reproducible builds

## [0.1.0] - 2024-XX-XX

### Added
- **Core Agent System**
  - Modular agent architecture with async execution
  - Dynamic agent loading from `user/agents/` directory
  - XML-based tool calling format
  - Parallel execution of multiple sub-agents and tools
  - Full conversation context management

- **Tool System**
  - `BaseTool` abstract class for creating tools
  - Dynamic tool loading from `user/tools/` directory
  - Built-in tools: calculator, text_analyzer, file_writer, file_reader, bash_executor

- **Database Tracking**
  - SQLite-based execution tracking
  - Agent execution history with parent-child relationships
  - Tool execution logging

- **LLM Client**
  - OpenAI-compatible API support
  - Configurable model, temperature, and API endpoint
  - Async LLM calls with thread pool execution

- **Web Interface**
  - FastAPI-based web UI
  - Real-time execution monitoring via WebSocket
  - Agent execution tree visualization
  - JSON log download

- **CLI Interface**
  - Run agents from command line
  - List available agents and tools
  - Show execution history

- **Prompt System**
  - YAML-based prompt configuration
  - Customizable system prompts, messages, and errors
  - Multi-language support through prompt files

- **Visualization**
  - Terminal-based execution tree visualizer
  - Live watch mode with configurable refresh interval
  - Tool call display with parameters

- **Example Agents**
  - coordinator: Main orchestrator agent
  - math_assistant: Mathematical calculations
  - writer_assistant: Text analysis and file writing
  - researcher: Complex multi-level research
  - web_search: Web searching capabilities
  - And more (16 agents total)

- **Example Tools**
  - calculator: Basic arithmetic operations
  - text_analyzer: Word/char/line counting
  - file_writer: File writing to output directory
  - file_reader: File content reading
  - web_fetcher: Web page fetching
  - bash_executor: Bash command execution
  - And more (11 tools total)

- **Documentation**
  - Comprehensive README with usage examples
  - CLAUDE.md for AI assistants
  - Detailed architecture documentation
  - Testing documentation and reports

### Security
- Environment-based configuration for API keys
- Comprehensive .gitignore for sensitive files
- Output directory isolation for file operations

---

[Unreleased]: https://github.com/YOUR_USERNAME/multi-agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_USERNAME/multi-agent/releases/tag/v0.1.0
