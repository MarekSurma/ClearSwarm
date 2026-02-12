"""
Main entry point for the multi-agent system.
Run with: python -m multi_agent
"""
import argparse
import asyncio
import sys
from pathlib import Path

from .core.agent import AgentLoader
from .tools.loader import ToolLoader
from .core.database import get_database
from .core.project import ProjectManager
from .core.prompts import set_prompt_loader, PromptLoader



async def async_main():
    """Async main function to run the multi-agent system."""
    parser = argparse.ArgumentParser(
        description="ClearSwarm with LLM (Async)"
    )
    parser.add_argument(
        "agent",
        nargs='?',
        help="Name of the agent to run"
    )
    parser.add_argument(
        "message",
        nargs='?',
        help="Message to send to the agent"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools"
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Show agent execution history"
    )
    parser.add_argument(
        "--prompts-file",
        type=str,
        default="default.yaml",
        help="Name of prompts YAML file in user/prompts/ directory (default: default.yaml)"
    )
    parser.add_argument(
        "--project",
        type=str,
        default="default",
        help="Project directory to use (default: default)"
    )

    args = parser.parse_args()

    # Initialize ProjectManager
    current_dir = Path.cwd()
    if (current_dir / "user").exists():
        user_dir = current_dir / "user"
    elif (current_dir.parent / "user").exists():
        user_dir = current_dir.parent / "user"
    else:
        user_dir = current_dir / "user"

    db = get_database()
    pm = ProjectManager(user_dir, db)

    # Get project-specific directories
    tools_dir = str(pm.get_tools_dir(args.project))
    agents_dir = str(pm.get_agents_dir(args.project))
    prompts_dir = str(pm.get_prompts_dir(args.project))

    # Initialize prompt loader with specified prompts file and directory
    prompt_loader = PromptLoader(prompts_file=args.prompts_file, prompts_dir=prompts_dir)
    set_prompt_loader(prompts_file=args.prompts_file, prompts_dir=prompts_dir)

    # Initialize loaders
    tool_loader = ToolLoader(tools_dir=tools_dir)
    tool_loader.load_tools()

    agent_loader = AgentLoader(
        agents_dir=agents_dir,
        tool_loader=tool_loader,
        prompt_loader=prompt_loader,
        project_dir=args.project
    )

    # Handle list commands
    if args.list_agents:
        print("Available agents:")
        for agent_name in agent_loader.get_available_agents():
            config = agent_loader.get_agent_config(agent_name)
            print(f"  - {agent_name}: {config.description}")
        return

    if args.list_tools:
        print("Available tools:")
        for tool_name, tool in tool_loader.get_all_tools().items():
            print(f"  - {tool_name}: {tool.description}")
        return

    if args.show_history:
        executions = db.get_all_executions(project_dir=args.project)
        print(f"Agent Execution History (Project: {args.project}):")
        print("-" * 80)
        for exec_info in executions:
            print(f"Agent: {exec_info['agent_name']} (ID: {exec_info['agent_id']})")
            print(f"Parent: {exec_info['parent_agent_name']}")
            print(f"Started: {exec_info['started_at']}")
            print(f"Completed: {exec_info['completed_at'] or 'Running...'}")
            print(f"Project: {exec_info.get('project_dir', 'default')}")
            print("-" * 80)
        return

    # If no info flags provided, agent and message are required
    if not args.agent or not args.message:
        parser.error("agent and message arguments are required")

    # Validate agent exists
    if not agent_loader.has_agent(args.agent):
        print(f"Error: Agent '{args.agent}' not found.")
        print("\nAvailable agents:")
        for agent_name in agent_loader.get_available_agents():
            print(f"  - {agent_name}")
        sys.exit(1)

    # Create and run agent asynchronously
    try:
        agent = agent_loader.create_agent(args.agent)
        result = await agent.run(args.message)

        print(f"\n{'='*80}")
        print(f"FINAL RESULT:")
        print(result)
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"ERROR RUNNING AGENT: {e}")
        print(f"{'='*80}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point that sets up asyncio event loop."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
