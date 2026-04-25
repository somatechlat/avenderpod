from __future__ import annotations

from agent import AgentContext


API_CONTEXT_OWNER_KEY = "_api_context_owner"
API_CONTEXT_OWNER_VALUE = "external_api"


def mark_external_api_context(context: AgentContext) -> None:
    context.set_data(API_CONTEXT_OWNER_KEY, API_CONTEXT_OWNER_VALUE)


def is_external_api_context(context: AgentContext) -> bool:
    return context.get_data(API_CONTEXT_OWNER_KEY) == API_CONTEXT_OWNER_VALUE
