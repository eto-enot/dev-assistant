import difflib as df
import logging
import os
from typing import Annotated

from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from workflows.runtime.types.results import WaitingForEvent

from .utils import get_tool_metadata, wait_for_event

TOOL_DESCRIPTION = """To edit (modify) an existing file use the edit_file tool. This tool performs \
exact string replacements in files.
- You must use your `read_file` tool at least once in the conversation before editing. This tool \
will error if you attempt an edit without reading the file.
- When editing text from `read_file` tool output, ensure you preserve the exact indentation \
(tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: \
line number + tab. Everything after that is the actual file content to match. Never include \
any part of the line number prefix in the old_string or new_string.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger \
string with more surrounding context to make it unique or use `replace_all` to change every \
instance of `old_string`.
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful \
if you want to rename a variable for instance.
Usage Cost: 20"""

logger = logging.getLogger(__name__)


def _normalize_quotes(s: str):
    return s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')


def _find_normalized_string(content: str, search_string: str):
    if search_string in content:
        return search_string

    content = _normalize_quotes(content)
    search_string = _normalize_quotes(search_string)
    if search_string in content:
        return search_string

    return None


def _apply_edit(content: str, old_string: str, new_string: str, replace_all: bool):
    prev_content = content
    if old_string == "":
        return new_string

    cnt = -1 if replace_all else 1
    if new_string != "":
        content = content.replace(old_string, new_string, cnt)
    else:
        strip_nl = not old_string.endswith("\n") and (old_string + "\n") in content
        content = content.replace(
            old_string + "\n" if strip_nl else old_string, new_string
        )

    if content == prev_content:
        raise ValueError("String not found in file. Failed to apply edit.")

    return content


def _get_patch(old_content: str, new_content: str):
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    diff = df.unified_diff(old_lines, new_lines, lineterm="")
    return "\n".join([x for x in diff])


class EditFileTool(FunctionTool):
    def __init__(self):
        """Edit file tool. Used for a file modification."""
        tool_metadata = get_tool_metadata(
            self._edit_file, "edit_file", TOOL_DESCRIPTION
        )
        super().__init__(self._edit_file, tool_metadata)

    async def _edit_file(
        self,
        ctx: Context,
        path: Annotated[
            str, "The relative file name or path to file being edited (modified)"
        ],
        old_string: Annotated[str, "The text to replace"],
        new_string: Annotated[
            str, "The text to replace it with (must be different from old_string)"
        ],
        replace_all: Annotated[
            bool, "Replace all occurrences of old_string (default false)"
        ] = False,
    ):
        logger.debug("EditFile tool called")
        try:
            work_dir = await ctx.store.get("work_dir", None)
            session_id = await ctx.store.get("session_id", None)
            if not work_dir:
                return (
                    f"I cannot edit the '{path}', working directory is not set. "
                    "Please ask user to set working directory."
                )

            logger.debug("Working directory: %s", work_dir)
            logger.debug("Session ID: %s", session_id)

            if old_string == new_string:
                return (
                    f"I cannot edit the '{path}': old_string and new_string are exactly "
                    "the same. No changes to make."
                )

            content = ""
            full_path = os.path.join(work_dir, path)
            if old_string != "":
                if not os.path.isfile(full_path) or not os.path.exists(full_path):
                    return (
                        f"File '{path}' doesn't exists. Please check the tool arguments "
                        "and try again, or choose an another tool."
                    )
                with open(full_path, "rt", encoding="utf-8") as f:
                    content = f.read().replace("\r\n", "\n")

            normalized_old = _find_normalized_string(content, old_string)
            if not normalized_old:
                return (
                    f"I cannot edit the '{path}': string to replace not found in file.\n"
                    f"String: {old_string}"
                )

            idx = content.index(normalized_old)
            try:
                idx = content.index(normalized_old, idx + 1)
                return (
                    f"I cannot edit the '{path}': found multiple matches of the string to "
                    "replace, but replace_all is false. To replace all occurrences, set "
                    "replace_all to true. To replace only one occurrence, please provide "
                    f"more context to uniquely identify the instance.\nString: {old_string}"
                )
            except ValueError:
                pass

            updated_content = _apply_edit(
                content, normalized_old, new_string, replace_all
            )
            question = (
                f"Apply the following editings to '{path}'?\n```diff\n"
                f"{_get_patch(content, updated_content)}```"
            )

            response = await wait_for_event(ctx, session_id, question)
            if not response.response:
                return (
                    f"User rejected the file modification. File '{path}' was NOT edited. "
                    + "So just print provided file content to User and stop conversation."
                )

            with open(full_path, "wt", encoding="utf-8") as f:
                f.write(updated_content)

            return f"File '{path}' modified successfully."
        except WaitingForEvent as e:
            raise e
        except Exception as e:
            return f"edit_file tool got the error during execution: {str(e)}"
