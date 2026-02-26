from pathlib import Path
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from .utils import get_tool_metadata

class FindFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
            self._find_file, "find_file",
            "Use this tool to find a file using its name or glob pattern. After that you can read file content with read_file tool. Cost: 10"
        )
        super().__init__(self._find_file, tool_metadata)

    async def _find_file(
        self,
        ctx: Context,
        name: Annotated[str, 'The name or glob pattern of the file we are looking for']):
        
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
