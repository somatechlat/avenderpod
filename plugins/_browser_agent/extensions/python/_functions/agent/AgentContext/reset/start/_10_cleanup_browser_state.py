from helpers.extension import Extension


class CleanupBrowserStateOnReset(Extension):
    def execute(self, **kwargs):
        data = kwargs.get("data") or {}
        args = data.get("args")
        if not isinstance(args, tuple) or not args:
            return

        context = args[0]
        state = context.get_data("_browser_agent_state")
        if state is not None and hasattr(state, "kill_task"):
            state.kill_task()
        context.set_data("_browser_agent_state", None)
