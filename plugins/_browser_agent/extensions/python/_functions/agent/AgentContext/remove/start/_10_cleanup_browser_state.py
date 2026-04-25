from helpers.extension import Extension


class CleanupBrowserStateOnRemove(Extension):
    def execute(self, **kwargs):
        data = kwargs.get("data") or {}
        context_id = _extract_context_id(data.get("args"))
        if not context_id:
            return

        from agent import AgentContext

        context = AgentContext.get(context_id)
        if context is not None:
            _kill_browser_state(context.get_data("_browser_agent_state"))


def _extract_context_id(args) -> str | None:
    if not isinstance(args, tuple) or not args:
        return None
    context_id = args[0]
    return context_id if isinstance(context_id, str) else None


def _kill_browser_state(state) -> None:
    if state is None or not hasattr(state, "kill_task"):
        return
    state.kill_task()
