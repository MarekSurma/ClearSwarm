# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of ClearSwarm seriously. If you discover a security vulnerability, please follow these steps:

### DO NOT

- Do not open a public GitHub issue for security vulnerabilities
- Do not disclose the vulnerability publicly until it has been addressed

### DO

1. **Email** the security issue to: [marek.surma@terabyterain.com]
   - Replace with your actual security contact email

2. **Include** in your report:
   - Type of vulnerability
   - Full path of affected source file(s)
   - Location of the affected source code (tag/branch/commit or direct URL)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the vulnerability

3. **Wait** for acknowledgment within 48 hours

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Status Update**: Within 7 days with our assessment
- **Resolution Timeline**: We aim to resolve critical vulnerabilities within 30 days

## Security Best Practices for Users

### API Keys

- **Never** commit `.env` files with real API keys
- Use `.env.example` as a template with placeholder values
- Store API keys in environment variables or secure secret managers
- Rotate API keys regularly

### Tool Execution

The system includes tools that can execute commands (e.g., `bash_executor`). Be aware:

- Only use trusted agents and tools
- Review agent prompts before deployment
- Limit tool permissions in production environments
- Monitor agent execution logs

### Database

- The SQLite database (`agents.db`) contains execution history
- Review and purge logs regularly if they contain sensitive information
- Do not expose the database file publicly

### Network

- When using local LLM servers, ensure they're not exposed to public networks
- Use HTTPS for remote API connections
- Configure firewalls appropriately

## Known Security Considerations

### Dynamic Code Loading

The system loads agents and tools dynamically from `user/agents/` and `user/tools/` directories. This is by design for extensibility but requires:

- Only add tools from trusted sources
- Review tool code before adding to the system
- Use file permissions to restrict write access to these directories

### LLM Prompt Injection

As with any LLM-based system, be aware of prompt injection risks:

- Sanitize user inputs when possible
- Use system prompts to enforce boundaries
- Monitor agent outputs for unexpected behavior

## Security Updates

Security updates will be released as:
- Patch versions for critical vulnerabilities
- Minor versions for non-critical security improvements

Subscribe to repository releases to stay informed about security updates.

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who help improve the project's security (with their permission).
