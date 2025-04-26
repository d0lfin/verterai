import logging
from typing import TypedDict

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langgraph.constants import START
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from coder.kotlinfile import UITestsKotlinFile
from utils import get_file_content


class ViewExtraction(BaseModel):
    """Model of files structure after extraction View class and refactoring"""
    actions: UITestsKotlinFile = Field(description="Actions for view component")
    assertions: UITestsKotlinFile = Field(description="Assertions for view component")
    view: UITestsKotlinFile = Field(description="View component view tree")
    screens_implementation: UITestsKotlinFile = Field(description="Implementation of Screens")


class ExtractorState(TypedDict):
    actions: UITestsKotlinFile
    assertions: UITestsKotlinFile
    view: UITestsKotlinFile
    screens_implementation: UITestsKotlinFile


class ViewExtractor:

    _extract_view_template = get_file_content("./coder/prompts/extract_view.md")
    _logger = logging.getLogger(__name__)
    _parser = PydanticOutputParser(pydantic_object=ViewExtraction)

    def __init__(self, model):
        graph_builder = StateGraph(ExtractorState)
        graph_builder.add_node("extract_view", self._extract_view)
        graph_builder.add_edge(START, "extract_view")

        self._graph = graph_builder.compile()
        self._model = model

    def _extract_view(self, state: ExtractorState) -> ExtractorState:
        parser = PydanticOutputParser(pydantic_object=ViewExtraction)
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(self._extract_view_template),
            HumanMessagePromptTemplate.from_template("""
# Actions class:
{actions}

# Assertions class:
{assertions}

# ScreensUiAutomator.kt:
{screens_implementation}

{format_instructions}
                """)
        ])

        request = prompt_template.invoke({
            "actions": state["actions"].source,
            "assertions": state["assertions"].source,
            "screens_implementation": state["screens_implementation"].source,
            "format_instructions": parser.get_format_instructions()
        })
        response = self._model.invoke(request)

        result: ViewExtraction = self._parser.parse(response.text())
        state["actions"] = result.actions
        state["assertions"] = result.assertions
        state["screens_implementation"] = result.screens_implementation
        state["view"] = result.view

        return state

    def extract(self,
                actions: UITestsKotlinFile,
                assertions: UITestsKotlinFile,
                screens: UITestsKotlinFile) -> ExtractorState:
        return self._graph.invoke({
            "actions": actions,
            "assertions": assertions,
            "screens_implementation": screens
        })
