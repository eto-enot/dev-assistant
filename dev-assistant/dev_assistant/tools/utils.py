from typing import Any, Callable
from llama_index.core.tools import ToolMetadata
from llama_index.core.tools.utils import create_schema_from_function


def get_tool_metadata(fn: Callable[..., Any], name: str, description: str):
    fn_schema = create_schema_from_function(
        name, fn, additional_fields=None,
        ignore_fields=["self", "ctx"],
    )

    return ToolMetadata(name=name, description=description, fn_schema=fn_schema)
