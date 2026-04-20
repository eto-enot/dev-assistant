import os
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from workflows.runtime.types.results import WaitingForEvent
from llama_index.core import Settings
from .utils import get_tool_metadata
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    LLMMetadata,
    TextBlock,
)

TOOL_DESCRIPTION = "To edit (modify) an existing file use the edit_file tool. " \
"If you don't know the contents of the file, read it first.\n" \
"When addressing code modification requests, present a concise code snippet that " \
"emphasizes only the necessary changes and uses abbreviated placeholders for " \
"unmodified sections. For example:\n" \
" ```language ./path/to/file\n" \
"  // ... existing code ...\n" \
"  {{ modified code here }}\n" \
"  // ... existing code ...\n" \
"  // ... rest of code ...\n" \
"  ```\n" \
"In existing files, you should always restate the function or class that the snippet belongs to:\n" \
"  ```language /path/to/file\n" \
"  // ... existing code ...\n" \
"  function exampleFunction() {\n" \
"  // ... existing code ...\n" \
"  {{ modified code here }}\n" \
"  // ... rest of function ...\n" \
"  }\n" \
"  // ... rest of code ...\n" \
"  ```\n"
"Since users have access to their complete file, they prefer reading only the " \
"relevant modifications. It's perfectly acceptable to omit unmodified portions " \
"at the beginning, middle, or end of files using these \"lazy\" comments. Only " \
"provide the complete file when explicitly requested. Include a concise explanation " \
"of changes unless the user specifically asks for code only.\n\n" \
"Usage Cost: 20"

class EditFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
            self._edit_file, "edit_file", TOOL_DESCRIPTION
        )
        super().__init__(self._edit_file, tool_metadata)

    async def _edit_file(
            self, ctx: Context,
            path: Annotated[str, "Relative file name or path to file being edited (modified)"],
            changes: Annotated[str, "Any modifications to the file, showing only needed changes. " \
                               "Do NOT wrap this in a codeblock or write anything besides the code changes. " \
                               "In larger files, use brief language-appropriate placeholders for large " \
                               "unmodified sections, e.g. '// ... existing code ...'"]):
        try:
            work_dir = await ctx.store.get('work_dir', None)
            session_id = await ctx.store.get('session_id', None)
            if not work_dir:
                return f"I cannot create the '{path}', working directory is not set. Please ask user to set working directory."
            print('work dir is:', work_dir)
            full_path = os.path.join(work_dir, path)
            if not os.path.isfile(full_path) or not os.path.exists(full_path):
                return f"File '{path}' doesn't exists. Please check the tool arguments and try again, or choose an another tool."
            
            response = await Settings.llm.achat([ChatMessage("Hello!")])
            return f"File '{path}' modified successfully."
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"edit_file tool got the error during execution: {str(e)}"
