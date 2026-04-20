import os
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from workflows.runtime.types.results import WaitingForEvent
from .utils import get_tool_metadata


TOOL_DESCRIPTION = "To write (create) a file into the local filesystem, use the `create_file` tool. \
This tool will overwrite the existing file if there is one at the provided path. \
Prefer the `edit_file` tool for modifying existing files - it only sends the diff. \
Only use this tool to create new files or for complete rewrites. \
\nUsage Cost: 20"
        

class CreateFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
            self._create_file, "create_file",
            TOOL_DESCRIPTION
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
            with open(full_path, 'wt', encoding='utf-8') as f:
                f.write(content)
            print('created!', full_path)
            return f"File '{path}' created successfully."
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"create_file tool got the error during execution: {str(e)}"