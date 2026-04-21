import logging
from typing import Annotated

from llama_index.core.tools import FunctionTool

from .utils import get_tool_metadata

logger = logging.getLogger("dev-assistant.tools")


class CalculatorTool(FunctionTool):
    def __init__(self):
        """Calculator tool. Used for arithmetic calculations"""
        tool_metadata = get_tool_metadata(
            self._calculator,
            "calculator",
            "Calculator, use it for arithmetic calculations. Usage Cost: 1",
        )
        super().__init__(self._calculator, tool_metadata)

    def _calculator(self, expression: Annotated[str, "Arithmetic expression"]):
        logger.debug("Calculator tool called")
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"calculator tool got the error during execution: {str(e)}"
