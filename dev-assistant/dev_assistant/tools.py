from pathlib import Path
from typing import Annotated, Any, Awaitable, Callable, Dict, Optional
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.tools.function_tool import AsyncCallable
from llama_index.core.tools.utils import create_schema_from_function
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from workflows.runtime.types.results import WaitingForEvent
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
            "Calculator, use it for arithmetic calculations. Usage Cost: 1"
        )
        super().__init__(self._calculator, tool_metadata)

    def _calculator(self, expression: Annotated[str, 'Arithmetic expression']):
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"calculator tool got the error during execution: {str(e)}"
        

class ReadFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._read_file, "read_file",
            "To read a file content with given file name or path, use the read_file tool. Usage Cost: 10"
        )
        super().__init__(self._read_file, tool_metadata)

    async def _read_file(self, ctx: Context, path: Annotated[str, 'Relative path to file or file name']):
        try:
            work_dir = await ctx.store.get('work_dir', None)
            if not work_dir:
                return f"I cannot read the {path}, working directory is not set. Please ask user to set working directory."
            
            full_path = os.path.join(work_dir, path)
            if not os.path.isfile(full_path):
                return f"File '{path}' does not exist."
            
            with open(full_path, 'rt') as f:
                return f"The content of '{path}' file is:\n\n" + f.read()
        except Exception as e:
            return f"read_file tool got the error during execution: {str(e)}"
        

class CreateFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._create_file, "create_file",
            "To create (write) a file with given file name or path and content string, use the create_file tool. Usage Cost: 20"
        )
        super().__init__(self._create_file, tool_metadata)

    async def _create_file(
            self, ctx: Context,
            path: Annotated[str, 'Relative file name or path to file being created (written)'],
            content: Annotated[str, 'Content of the created file']):
        try:
            work_dir = await ctx.store.get('work_dir', None)
            session_id = await ctx.store.get('session_id', None)
            if not work_dir:
                return f"I cannot create the '{path}', working directory is not set. Please ask user to set working directory."
            print('work dir is:', work_dir)
            full_path = os.path.join(work_dir, path)
            if os.path.isfile(full_path):
                question = f"File '{path}' already exists. Overwrite?"
                response = await ctx.wait_for_event(
                    HumanResponseEvent,
                    waiter_id=question,
                    waiter_event=InputRequiredEvent(
                        prefix=question,
                        session_id=session_id,
                    ),
                    requirements={"session_id": session_id}
                )
                if not response.response:
                    return f"User rejected the file creation. File '{path}' was NOT created. " + \
                        "So just print provided file content to User and stop conversation."
            with open(full_path, 'wt') as f:
                f.write(content)
            print('created!', full_path)
            return f"File '{path}' created successfully."
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"create_file tool got the error during execution: {str(e)}"
        

class ListFilesTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._list_files, "list_files",
            "Use this tool to list files and folders in a given directory. Directories names ends with slash symbol '/'. Cost: 2"
        )
        super().__init__(self._list_files, tool_metadata)

    async def _list_files(
        self,
        ctx: Context,
        directory: Annotated[str, 'The directory for which you want to list files and folders'],
        recursive: Annotated[bool, 'List files for all subdirectories as well'] = False):
        
        try:
            work_dir = await ctx.store.get('work_dir', None)
            if not work_dir:
                return f"I cannot list directory '{directory}' since working directory is not set. Please ask user to set working directory."
            
            print('work dir is:', work_dir)
            abs_path = Path(directory).resolve()
            if not abs_path.exists() or not abs_path.is_dir():
                return f"Directory {directory} does not exist."
            
            files = []
            if recursive:
                for item in abs_path.rglob('*'):
                    rel_path = item.relative_to(abs_path)
                    name = str(rel_path)
                    if item.is_dir():
                        name += '/'
                    files.append(name)
            else:
                for item in abs_path.iterdir():
                    name = item.name
                    if item.is_dir():
                        name += '/'
                    files.append(name)

            return '\n'.join(files)
        except Exception as e:
                return f"list_files tool got the error during execution: {str(e)}"
        
class FindFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = _get_tool_metadata(
            self._find_file, "find_file",
            "Use this tool to find file with given name. After that you can read file content with read_file tool. Cost: 10"
        )
        super().__init__(self._find_file, tool_metadata)

    async def _find_file(
        self,
        ctx: Context,
        name: Annotated[str, 'The name of the file we are looking for']):
        
        try:
            work_dir = await ctx.store.get('work_dir', None)
            if not work_dir:
                return f"Error: working directory is not set. Please ask user to set working directory."
            
            print('work dir is:', work_dir)
            abs_path = Path(work_dir).resolve()
            for item in abs_path.rglob(name, case_sensitive=False):
                rel_path = item.relative_to(abs_path)
                return f'Found file: {str(rel_path)}'
            return f"File '{name}' not found"
        except Exception as e:
                return f"find_file tool got the error during execution: {str(e)}"