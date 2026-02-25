import os
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from workflows.runtime.types.results import WaitingForEvent
from .utils import get_tool_metadata
        

class CreateFileTool(FunctionTool):
    def __init__(self):
        tool_metadata = get_tool_metadata(
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