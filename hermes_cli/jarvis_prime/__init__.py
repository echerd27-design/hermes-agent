"""JARVIS Prime workspace layer for ACI products.

Wave 13 introduces the stdlib-only :class:`Workspace` schema and the
five built-in product templates (Nourish, HazMat Command, Hey Jay,
Hermes Core, ACI Internal). Later waves layer routing, memory, and
release gates on top of this package.

Importing this package has no side effects.
"""

from hermes_cli.jarvis_prime.workspaces import (
    Workspace,
    create_workspace_from_template,
    get_workspace_template,
    list_workspace_templates,
)

__all__ = [
    "Workspace",
    "create_workspace_from_template",
    "get_workspace_template",
    "list_workspace_templates",
]
