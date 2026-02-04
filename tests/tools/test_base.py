"""Tests for tool base classes."""
import pytest
from abc import ABC

from multi_agent.tools.base import BaseTool


class TestBaseTool:
    """Test cases for BaseTool abstract class."""

    def test_base_tool_is_abstract(self):
        """Test that BaseTool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTool()

    def test_concrete_tool_implementation(self):
        """Test that a concrete tool can be implemented."""

        class ConcreteTool(BaseTool):
            @property
            def name(self) -> str:
                return "test_tool"

            @property
            def description(self) -> str:
                return "A test tool for testing"

            def execute(self, **kwargs) -> str:
                return "executed"

        tool = ConcreteTool()
        assert tool.name == "test_tool"
        assert tool.description == "A test tool for testing"
        assert tool.execute() == "executed"

    def test_missing_name_property(self):
        """Test that missing name property prevents instantiation."""

        class IncompleteTool(BaseTool):
            @property
            def description(self) -> str:
                return "Description"

            def execute(self, **kwargs) -> str:
                return "result"

        with pytest.raises(TypeError):
            IncompleteTool()

    def test_missing_description_property(self):
        """Test that missing description property prevents instantiation."""

        class IncompleteTool(BaseTool):
            @property
            def name(self) -> str:
                return "tool"

            def execute(self, **kwargs) -> str:
                return "result"

        with pytest.raises(TypeError):
            IncompleteTool()

    def test_missing_execute_method(self):
        """Test that missing execute method prevents instantiation."""

        class IncompleteTool(BaseTool):
            @property
            def name(self) -> str:
                return "tool"

            @property
            def description(self) -> str:
                return "Description"

        with pytest.raises(TypeError):
            IncompleteTool()


class TestBaseToolToFunctionDefinition:
    """Test cases for to_function_definition method."""

    def test_auto_generate_from_signature(self):
        """Test automatic parameter schema generation from method signature."""

        class SimpleCalculator(BaseTool):
            @property
            def name(self) -> str:
                return "calculator"

            @property
            def description(self) -> str:
                return "Performs basic calculations"

            def execute(self, a: int, b: int, operation: str = "add") -> str:
                if operation == "add":
                    return str(a + b)
                return "unknown"

        tool = SimpleCalculator()
        func_def = tool.to_function_definition()

        assert func_def["type"] == "function"
        assert func_def["function"]["name"] == "calculator"
        assert func_def["function"]["description"] == "Performs basic calculations"

        params = func_def["function"]["parameters"]
        assert params["type"] == "object"
        assert "a" in params["properties"]
        assert "b" in params["properties"]
        assert "operation" in params["properties"]

        # Check types
        assert params["properties"]["a"]["type"] == "integer"
        assert params["properties"]["b"]["type"] == "integer"
        assert params["properties"]["operation"]["type"] == "string"

        # Check required parameters (operation has default, so not required)
        assert "a" in params["required"]
        assert "b" in params["required"]
        assert "operation" not in params["required"]

    def test_auto_generate_with_float_type(self):
        """Test that float annotation maps to 'number' type."""

        class FloatTool(BaseTool):
            @property
            def name(self) -> str:
                return "float_tool"

            @property
            def description(self) -> str:
                return "Tool with float parameter"

            def execute(self, value: float) -> str:
                return str(value)

        tool = FloatTool()
        func_def = tool.to_function_definition()

        assert func_def["function"]["parameters"]["properties"]["value"]["type"] == "number"

    def test_auto_generate_with_bool_type(self):
        """Test that bool annotation maps to 'boolean' type."""

        class BoolTool(BaseTool):
            @property
            def name(self) -> str:
                return "bool_tool"

            @property
            def description(self) -> str:
                return "Tool with boolean parameter"

            def execute(self, enabled: bool) -> str:
                return str(enabled)

        tool = BoolTool()
        func_def = tool.to_function_definition()

        assert func_def["function"]["parameters"]["properties"]["enabled"]["type"] == "boolean"

    def test_auto_generate_with_no_type_annotation(self):
        """Test that parameters without type annotation default to 'string'."""

        class NoTypeTool(BaseTool):
            @property
            def name(self) -> str:
                return "no_type_tool"

            @property
            def description(self) -> str:
                return "Tool without type annotations"

            def execute(self, param) -> str:
                return str(param)

        tool = NoTypeTool()
        func_def = tool.to_function_definition()

        assert func_def["function"]["parameters"]["properties"]["param"]["type"] == "string"

    def test_custom_parameters_schema(self):
        """Test that custom parameter schema overrides auto-generation."""

        class CustomSchemaTool(BaseTool):
            @property
            def name(self) -> str:
                return "custom_tool"

            @property
            def description(self) -> str:
                return "Tool with custom schema"

            def execute(self, **kwargs) -> str:
                return "executed"

            def get_parameters_schema(self):
                return {
                    "type": "object",
                    "properties": {
                        "custom_param": {
                            "type": "string",
                            "description": "A custom parameter"
                        }
                    },
                    "required": ["custom_param"]
                }

        tool = CustomSchemaTool()
        func_def = tool.to_function_definition()

        assert func_def["function"]["name"] == "custom_tool"
        assert "custom_param" in func_def["function"]["parameters"]["properties"]
        assert func_def["function"]["parameters"]["properties"]["custom_param"]["description"] == "A custom parameter"
        assert "custom_param" in func_def["function"]["parameters"]["required"]

    def test_no_parameters_tool(self):
        """Test tool with no parameters."""

        class NoParamsTool(BaseTool):
            @property
            def name(self) -> str:
                return "no_params"

            @property
            def description(self) -> str:
                return "Tool with no parameters"

            def execute(self) -> str:
                return "executed"

        tool = NoParamsTool()
        func_def = tool.to_function_definition()

        assert func_def["function"]["parameters"]["properties"] == {}
        assert func_def["function"]["parameters"]["required"] == []

    def test_get_parameters_schema_default_none(self):
        """Test that default get_parameters_schema returns None."""

        class SimpleTool(BaseTool):
            @property
            def name(self) -> str:
                return "simple"

            @property
            def description(self) -> str:
                return "Simple tool"

            def execute(self) -> str:
                return "result"

        tool = SimpleTool()
        assert tool.get_parameters_schema() is None
