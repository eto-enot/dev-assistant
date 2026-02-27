import os
import platform
import subprocess
from typing import Annotated
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from workflows.runtime.types.results import WaitingForEvent
from .utils import get_tool_metadata


class RunTerminalCommandTool(FunctionTool):
    def __init__(self):
        system = platform.system()
        shell = 'powershell' if platform.system() == 'Windows' else '/bin/bash'
        tool_metadata = get_tool_metadata(
            self._run_terminal_command, "run_terminal_command",
            "Run a terminal command in the current directory.\nThe shell is not stateful and will " +
            "not remember any previous commands. Choose terminal commands and scripts optimized for " +
            f"{system} and shell {shell}. Usage Cost: 20"
        )
        super().__init__(self._run_terminal_command, tool_metadata)

    async def _run_terminal_command(
            self, ctx: Context,
            command: Annotated[str, 'The command to run']
        ):
        
        try:
            work_dir = await ctx.store.get('work_dir', None)
            session_id = await ctx.store.get('session_id', None)
            if not work_dir:
                return f"I run the command, working directory is not set. Please ask user to set working directory."
            
            question = f"Assistant wants to execute '{command}' command. Continue?"
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
                return f"User rejected command execution. Please try another approach."
            
            system = platform.system()
            if system == 'Windows':
                cmd = ["powershell", "-NoLogo", "-ExecutionPolicy", "Bypass", "-Command", "chcp 65001>nil;", command]
            else:
                cmd = ["/bin/bash", "-l", "-c", command]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
            out_text = result.stdout if result.returncode == 0 else result.stderr

            return "Command execution result:\n" + out_text
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"run_terminal_command tool got the error during execution: {str(e)}"