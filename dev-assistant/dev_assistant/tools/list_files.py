from pathlib import Path
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from .utils import get_tool_metadata

MAX_LINES = 50
        
class ListFilesTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
            self._list_files, "list_files",
            "Use this tool to list files and folders in a given directory. Directories names ends with slash symbol '/'. Usage Cost: 2"
        )
        super().__init__(self._list_files, tool_metadata)

    async def _list_files(
        self,
        ctx: Context,
        directory: Annotated[str, 'The directory for which you want to list files and folders'],
        recursive: Annotated[bool, 'if false - list files only in specified directory\nif true - list files for all subdirectories as well (recursively)'] = False):
        
        try:
            work_dir = await ctx.store.get('work_dir', None)
            if not work_dir:
                return f"I cannot list directory '{directory}' since working directory is not set. Please ask user to set working directory."
            
            print('work dir is:', work_dir)
            abs_path = (Path(work_dir) / Path(directory)).resolve()
            print('listing dir:', abs_path)
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

            result = ''
            if len(files) > MAX_LINES:
                result = f'{MAX_LINES - len(files)} lines were truncated. Try to use a non-recursive search.\n'
                files = files[:MAX_LINES]

            result += '\n'.join(files)

            return result
        except Exception as e:
                return f"list_files tool got the error during execution: {str(e)}"
