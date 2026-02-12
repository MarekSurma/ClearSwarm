"""
Project management module for multi-project support.
Handles project directory resolution, creation, cloning, and deletion.
"""
import re
import shutil
from pathlib import Path
from typing import Dict, List
from multi_agent.core.database import AgentDatabase


def generate_safe_dirname(name: str, existing_dirs: List[str]) -> str:
    """
    Generate a filesystem-safe directory name from a project name.

    Args:
        name: Project name to convert
        existing_dirs: List of existing directory names to avoid collisions

    Returns:
        Safe directory name (lowercase, alphanumeric + _ -, max 50 chars)
    """
    # Convert to lowercase
    safe_name = name.lower()

    # Replace spaces with underscores
    safe_name = safe_name.replace(' ', '_')

    # Keep only alphanumeric, underscore, and hyphen
    safe_name = re.sub(r'[^a-z0-9_-]', '', safe_name)

    # Truncate to 50 characters
    safe_name = safe_name[:50]

    # Remove trailing underscores/hyphens
    safe_name = safe_name.rstrip('_-')

    # Ensure it's not empty
    if not safe_name:
        safe_name = "project"

    # Handle collisions by appending _2, _3, etc.
    original_name = safe_name
    counter = 2
    while safe_name in existing_dirs:
        safe_name = f"{original_name}_{counter}"
        counter += 1

    return safe_name


class ProjectManager:
    """Manages multi-project directory structure and operations."""

    def __init__(self, user_dir: Path, db: AgentDatabase):
        """
        Initialize project manager.

        Args:
            user_dir: Base user directory (e.g., 'user/')
            db: Database instance for project metadata
        """
        self.user_dir = Path(user_dir)
        self.db = db

    def validate_default_exists(self) -> None:
        """
        Validate that the default project exists.

        Raises:
            ValueError: If default project directory doesn't exist
        """
        default_dir = self.user_dir / "default"
        if not default_dir.exists():
            raise ValueError(
                f"Default project directory not found at {default_dir}. "
                "Please ensure user/default/ exists with agents/ subdirectory."
            )

        agents_dir = default_dir / "agents"
        if not agents_dir.exists():
            raise ValueError(
                f"Default agents directory not found at {agents_dir}. "
                "Please ensure user/default/agents/ exists."
            )

    def get_project_base_dir(self, project_dir: str) -> Path:
        """
        Get the base directory for a project.

        Args:
            project_dir: Project directory name

        Returns:
            Path to project directory
        """
        return self.user_dir / project_dir

    def get_agents_dir(self, project_dir: str) -> Path:
        """
        Get the agents directory for a project.

        Args:
            project_dir: Project directory name

        Returns:
            Path to agents directory (always project-specific, no fallback)
        """
        return self.get_project_base_dir(project_dir) / "agents"

    def get_tools_dir(self, project_dir: str) -> Path:
        """
        Get the tools directory for a project with fallback to default.

        Args:
            project_dir: Project directory name

        Returns:
            Path to tools directory (falls back to default if not exists)
        """
        project_tools = self.get_project_base_dir(project_dir) / "tools"
        if project_tools.exists():
            return project_tools
        # Fallback to default
        return self.user_dir / "default" / "tools"

    def get_prompts_dir(self, project_dir: str) -> Path:
        """
        Get the prompts directory for a project with fallback to default.

        Args:
            project_dir: Project directory name

        Returns:
            Path to prompts directory (falls back to default if not exists)
        """
        project_prompts = self.get_project_base_dir(project_dir) / "prompts"
        if project_prompts.exists():
            return project_prompts
        # Fallback to default
        return self.user_dir / "default" / "prompts"

    def create_project(
        self,
        name: str,
        create_tools: bool = False,
        create_prompts: bool = False
    ) -> Dict:
        """
        Create a new project.

        Args:
            name: Display name for the project
            create_tools: Whether to create a tools directory
            create_prompts: Whether to create a prompts directory

        Returns:
            Project info dictionary

        Raises:
            ValueError: If project already exists
        """
        # Generate safe directory name
        existing_projects = self.db.get_all_projects()
        existing_dirs = [p['project_dir'] for p in existing_projects]
        project_dir = generate_safe_dirname(name, existing_dirs)

        # Create database entry first
        self.db.create_project(name, project_dir)

        # Create filesystem directories
        project_path = self.get_project_base_dir(project_dir)
        project_path.mkdir(parents=True, exist_ok=True)

        # Always create agents directory (required)
        agents_dir = project_path / "agents"
        agents_dir.mkdir(exist_ok=True)

        # Optionally create tools directory
        if create_tools:
            tools_dir = project_path / "tools"
            tools_dir.mkdir(exist_ok=True)

        # Optionally create prompts directory
        if create_prompts:
            prompts_dir = project_path / "prompts"
            prompts_dir.mkdir(exist_ok=True)

        # Return full project info from database (includes created_at)
        return self.db.get_project_by_name(name)

    def clone_project(
        self,
        source_dir: str,
        new_name: str,
        clone_tools: bool = False,
        clone_prompts: bool = False
    ) -> Dict:
        """
        Clone an existing project.

        Args:
            source_dir: Source project directory name
            new_name: Display name for the new project
            clone_tools: Whether to clone the tools directory
            clone_prompts: Whether to clone the prompts directory

        Returns:
            New project info dictionary

        Raises:
            ValueError: If source project doesn't exist or new project already exists
        """
        # Validate source exists
        source_path = self.get_project_base_dir(source_dir)
        if not source_path.exists():
            raise ValueError(f"Source project directory '{source_dir}' not found")

        # Generate safe directory name for new project
        existing_projects = self.db.get_all_projects()
        existing_dirs = [p['project_dir'] for p in existing_projects]
        new_project_dir = generate_safe_dirname(new_name, existing_dirs)

        # Create database entry
        self.db.create_project(new_name, new_project_dir)

        # Create new project directory
        new_project_path = self.get_project_base_dir(new_project_dir)
        new_project_path.mkdir(parents=True, exist_ok=True)

        # Always clone agents directory
        source_agents = source_path / "agents"
        if source_agents.exists():
            dest_agents = new_project_path / "agents"
            shutil.copytree(source_agents, dest_agents, dirs_exist_ok=True)
        else:
            # Create empty agents dir if source doesn't have one
            (new_project_path / "agents").mkdir(exist_ok=True)

        # Optionally clone tools directory
        if clone_tools:
            source_tools = source_path / "tools"
            if source_tools.exists():
                dest_tools = new_project_path / "tools"
                shutil.copytree(source_tools, dest_tools, dirs_exist_ok=True)

        # Optionally clone prompts directory
        if clone_prompts:
            source_prompts = source_path / "prompts"
            if source_prompts.exists():
                dest_prompts = new_project_path / "prompts"
                shutil.copytree(source_prompts, dest_prompts, dirs_exist_ok=True)

        # Return full project info from database (includes created_at)
        return self.db.get_project_by_name(new_name)

    def delete_project(self, project_name: str) -> None:
        """
        Delete a project (both database and filesystem).

        Args:
            project_name: Name of the project to delete

        Raises:
            ValueError: If trying to delete default project or project not found
        """
        # Database will validate and raise if trying to delete default
        project = self.db.get_project_by_name(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_dir = project['project_dir']

        # Delete from database
        self.db.delete_project(project_name)

        # Delete filesystem directory
        project_path = self.get_project_base_dir(project_dir)
        if project_path.exists():
            shutil.rmtree(project_path)

    def list_projects(self) -> List[Dict]:
        """
        List all projects.

        Returns:
            List of project info dictionaries
        """
        return self.db.get_all_projects()
