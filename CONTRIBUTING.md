# Contributing to ClearSwarm

Thank you for your interest in contributing to ClearSwarm! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists in [GitHub Issues](../../issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (OS, Python version)

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would benefit the project

### Submitting Pull Requests

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following our coding standards
5. **Test** your changes:
   ```bash
   pytest tests/ -v
   ```
6. **Commit** with clear messages:
   ```bash
   git commit -m "Add: description of what you added"
   ```
7. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** against the `main` branch

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/multi-agent.git
cd multi-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API credentials
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=multi_agent --cov-report=html

# Run specific test file
pytest tests/core/test_agent.py -v
```

### Code Quality

Before submitting, ensure your code passes all checks:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/
pylint src/

# Type checking
mypy src/
```

Or use the Makefile:

```bash
make format   # Format code
make lint     # Run linters
make test     # Run tests
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Maximum line length: 100 characters

### Type Hints

- Use type hints for function parameters and return values
- Use `Optional[T]` for nullable types
- For Python 3.8 compatibility, import from `typing`:
  ```python
  from typing import List, Dict, Optional
  ```

### Docstrings

- Use docstrings for all public classes and methods
- Follow Google-style docstrings:
  ```python
  def function(param1: str, param2: int) -> bool:
      """Short description.

      Longer description if needed.

      Args:
          param1: Description of param1.
          param2: Description of param2.

      Returns:
          Description of return value.

      Raises:
          ValueError: When something is wrong.
      """
  ```

### Error Handling

- Catch specific exceptions, not bare `Exception`
- Provide meaningful error messages
- Use logging instead of print statements

## Creating Agents

To contribute a new agent:

1. Create a directory in `user/agents/your_agent_name/`
2. Add required files:
   - `description.txt` - Brief description for other agents
   - `system_prompt.txt` - Agent's system prompt
   - `tools.txt` - List of available tools (one per line)
3. Test your agent thoroughly
4. Document usage in the PR description

## Creating Tools

To contribute a new tool:

1. Create a file in `user/tools/your_tool.py`
2. Inherit from `BaseTool`:
   ```python
   from multi_agent.tools.base import BaseTool

   class YourTool(BaseTool):
       @property
       def name(self) -> str:
           return "your_tool"

       @property
       def description(self) -> str:
           return "Description of what your tool does"

       def execute(self, **kwargs) -> str:
           # Implementation
           return "result"
   ```
3. Add tests in `tests/tools/`
4. Document usage in the PR description

## Commit Message Format

Use clear, descriptive commit messages:

- `Add:` for new features
- `Fix:` for bug fixes
- `Update:` for updates to existing features
- `Remove:` for removed features
- `Docs:` for documentation changes
- `Test:` for test-related changes
- `Refactor:` for code refactoring

Example:
```
Add: web search tool with Tavily API support

- Implement TavilySearchTool class
- Add rate limiting for API calls
- Include comprehensive error handling
```

## Questions?

If you have questions, feel free to:
- Open an issue with the `question` label
- Start a discussion in GitHub Discussions

Thank you for contributing!
