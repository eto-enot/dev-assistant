import os
from typing import Annotated
from llama_index.core import Settings
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from .utils import get_tool_metadata

        
class ReadFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
            self._read_file, "read_file",
            "To read a file content with given file name or path, use the read_file tool. " \
            "The user can explicitly provide the contents of some files in which case there "
            "is no need to call this tool. Usage Cost: 10"
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
            
            with open(full_path, 'rt', encoding='utf-8') as f:
                content = f.read()

            tokens = Settings.tokenizer(content)
            if len(tokens) > Settings.context_window // 2:
                return f"The file {path} is too large. Please try another approach."
            
            return f"The content of '{path}' file is:\n\n" + content
        except Exception as e:
            return f"read_file tool got the error during execution: {str(e)}"
