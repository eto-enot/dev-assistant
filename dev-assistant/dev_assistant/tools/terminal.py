import logging
import platform
import subprocess
from typing import Annotated

from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from workflows.runtime.types.results import WaitingForEvent

from .utils import get_tool_metadata, wait_for_event

TOOL_DESCRIPTION = """Run a terminal command in the current directory. The shell is not stateful \
and will not remember any previous commands. Choose terminal commands and scripts optimized for \
{system}. The shell is {shell}.
Usage Cost: 20"""

logger = logging.getLogger(__name__)


class RunTerminalCommandTool(FunctionTool):
    def __init__(self):
        """Run command tool. Executes a given command"""
        system = platform.system()
        shell = "powershell" if platform.system() == "Windows" else "/bin/bash"
        description = TOOL_DESCRIPTION.format(system=system, shell=shell)
        tool_metadata = get_tool_metadata(
            self._run_terminal_command, "run_terminal_command", description
        )
        super().__init__(self._run_terminal_command, tool_metadata)

    async def _run_terminal_command(
        self, ctx: Context, command: Annotated[str, "The command to run"]
    ):
        logger.debug("RunTerminal tool called")
        try:
            work_dir = await ctx.store.get("work_dir", None)
            session_id = await ctx.store.get("session_id", None)
            if not work_dir:
                return "I run the command, working directory is not set. \
                    Please ask user to set working directory."

            logger.debug("Working directory: %s", work_dir)
            logger.debug("Session ID: %s", session_id)

            question = f"Assistant wants to execute '{command}' command. Continue?"
            response = await wait_for_event(ctx, session_id, question)

            if not response.response:
                logger.debug("Command execution rejected")
                return "User rejected command execution. Please try another approach."

            system = platform.system()
            if system == "Windows":
                cmd = [
                    "powershell",
                    "-NoLogo",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    f"chcp 65001>nil;cd '{work_dir}';",
                    command,
                ]
            else:
                cmd = ["/bin/bash", "-l", "-c", command]

            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
            )
            out_text = result.stdout if result.returncode == 0 else result.stderr

            return "Command execution result:\n" + out_text
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"run_terminal_command tool got the error during execution: {str(e)}"
