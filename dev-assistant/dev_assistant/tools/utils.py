from typing import Any, Callable

from llama_index.core.tools import ToolMetadata
from llama_index.core.tools.utils import create_schema_from_function
from llama_index.core.workflow import (Context, HumanResponseEvent,
                                       InputRequiredEvent)


def get_tool_metadata(fn: Callable[..., Any], name: str, description: str):
    """Get tool metadata for LLM"""

    fn_schema = create_schema_from_function(
        name,
        fn,
        additional_fields=None,
        ignore_fields=["self", "ctx"],
    )

    return ToolMetadata(name=name, description=description, fn_schema=fn_schema)


async def wait_for_event(ctx: Context, session_id: str, question: str):
    """Emit tool confirmation event"""

    return await ctx.wait_for_event(
        HumanResponseEvent,
        waiter_id=question,
        waiter_event=InputRequiredEvent(
            prefix=question,  # type: ignore
            session_id=session_id,  # type: ignore
        ),
        requirements={"session_id": session_id},
    )
