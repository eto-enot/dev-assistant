from typing import Annotated, Any, Awaitable, Callable, Dict, Optional
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.tools.function_tool import AsyncCallable
from llama_index.core.tools.utils import create_schema_from_function
from llama_index.core.workflow import Context
import os

def _get_tool_metadata(fn: Callable[..., Any], name: str, description: str):
    fn_schema = create_schema_from_function(
        name, fn, additional_fields=None,
        ignore_fields=["self", "ctx"],
    )
    return ToolMetadata(name=name, description=description, fn_schema=fn_schema)

class DangerousFunctionTool(FunctionTool):
    def __init__(
        self,
        fn: Optional[Callable[..., Any]] = None,
        metadata: Optional[ToolMetadata] = None,
        async_fn: Optional[AsyncCallable] = None,
        callback: Optional[Callable[..., Any]] = None,
        async_callback: Optional[Callable[..., Any]] = None,
        partial_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(fn, metadata, async_fn, callback, async_callback, partial_params)

class CalculatorTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._calculator, "calculator",
            "Calculator, use it for arithmetic calculations."
        )
        super().__init__(self._calculator, tool_metadata)

    def _calculator(self, expression: Annotated[str, 'Arithmetic expression']):
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"
        

class ReadFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._read_file, "read_file",
            "read_file(self, ctx: Context, path: Annotated[str, 'Relative path to file or file name'])\n" \
            "To read a file with a known file path or name, use the read_file tool."
        )
        super().__init__(self._read_file, tool_metadata)

    async def _read_file(self, ctx: Context, path: Annotated[str, 'Relative path to file or file name']):
        work_dir = await ctx.store.get('work_dir', None)
        if not work_dir:
            return f"I cannot read the {path}, working directory is not set. Please ask user to set working directory."
        
        full_path = os.path.join(work_dir, path)
        if not os.path.isfile(full_path):
            return f"File '{path}' does not exist."
        
        with open(full_path, 'rt') as f:
            return f"The content of '{path}' file is:\n\n" + f.read()