import json
import logging
import re
from collections import defaultdict
from typing import List, TypedDict

from anthropic import BaseModel
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from pydantic import Field

from action_frame import ActionFrame
from coder.kotlinfile import UITestsKotlinFile
from coder.viewextractor import ViewExtractor
from utils import get_file_content
from viewnode import without_fields


class ProjectFiles(BaseModel):
    """Model of android ui autotests project files"""
    kotlin_files: List[UITestsKotlinFile] = Field(description="List of autotests project files")


class CoderState(TypedDict):
    scenario: str
    actions: list[dict]
    interfaces: list[UITestsKotlinFile]
    implementation: list[UITestsKotlinFile]
    refactoring_index: int


class Automator:

    _logger = logging.getLogger(__name__)
    _parser = PydanticOutputParser(pydantic_object=ProjectFiles)
    _create_dsl_interfaces_template = get_file_content("./coder/prompts/create_dsl_interfaces.md")
    _create_implementation_template = get_file_content("./coder/prompts/create_implementation_uiautomator.md")
    _refactoring_template = get_file_content("./coder/prompts/uiautomator_refactoring.md")

    def __init__(self, model: BaseChatModel):
        graph_builder = StateGraph(CoderState)

        graph_builder.add_node("create_interfaces", self._create_interfaces)
        graph_builder.add_node("create_implementation", self._create_implementation)
        graph_builder.add_node("refactoring", self._refactoring)
        graph_builder.add_node("extract_views", self._extract_views)

        graph_builder.add_edge(START, "create_interfaces")
        graph_builder.add_edge("create_interfaces", "create_implementation")
        graph_builder.add_conditional_edges("create_implementation", self._refactoring_needed)
        graph_builder.add_conditional_edges("refactoring", self._refactoring_needed)
        graph_builder.add_edge("extract_views", END)

        self._graph = graph_builder.compile()
        self._view_extractor = ViewExtractor(model)
        self._model = model

    def _create_interfaces(self, state: CoderState) -> CoderState:
        user_actions = [
            {k: v for k, v in action.items() if k != "element_xpath"} for action in state["actions"]
        ]
        request = PromptTemplate.from_template(self._create_dsl_interfaces_template).invoke({
            "scenario": state["scenario"],
            "user_actions": json.dumps(user_actions, indent=None),
            "format_instructions": self._parser.get_format_instructions()
        })
        response = self._model.invoke(request)

        self._logger.info(f"Write interfaces: {response.usage_metadata}")
        state["interfaces"] = self._parser.parse(response.text()).kotlin_files
        return state

    def _create_implementation(self, state: CoderState) -> CoderState:
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(self._create_implementation_template),
            HumanMessagePromptTemplate.from_template("""
Interfaces:
{interfaces}

Test Scenario:
{scenario}

User Interactions:
{user_actions}

{format_instructions}
                    """)
        ])

        user_actions = [
            {k: v for k, v in action.items() if k != "screen_description"}
            for action in state["actions"]
        ]
        request = prompt_template.invoke({
            "interfaces": "\n\n".join(
                [f"// {file.relative_filepath}\n{file.source}" for file in state["interfaces"]]
            ),
            "scenario": state["scenario"],
            "user_actions": json.dumps(user_actions, indent=None),
            "format_instructions": self._parser.get_format_instructions()
        })
        response = self._model.invoke(request)

        self._logger.info(f"Write implementation: {response.usage_metadata}")
        state["implementation"] = self._parser.parse(response.text()).kotlin_files
        state["refactoring_index"] = 0
        return state

    def _refactoring_needed(self, state: CoderState) -> str:
        if state["refactoring_index"] < len(state["implementation"]):
            return "refactoring"
        else:
            return "extract_views"

    def _refactoring(self, state: CoderState) -> CoderState:
        file = state["implementation"][state["refactoring_index"]]
        file.source = self._model.invoke([
            SystemMessage(self._refactoring_template),
            HumanMessage(f"### Source code:\n{file.source}")
        ]).text()
        state["refactoring_index"] += 1
        return state

    @staticmethod
    def _group_by_component(file_list) -> dict[str]:
        result = defaultdict(lambda: {"actions": {}, "assertions": {}})
        screens = None

        for file_info in file_list:
            path = file_info.relative_filepath
            match = re.search(r"implementation/([^/]+)/([^/]+)", path)
            if match:
                component, filename = match.groups()
                if filename.endswith("Actions.kt"):
                    result[component]["actions"] = file_info
                elif filename.endswith("Assertions.kt"):
                    result[component]["assertions"] = file_info

            elif path.endswith("ScreensUiAutomator.kt"):
                screens = file_info

        result["screens_implementation"] = screens
        return result

    def _extract_views(self, state: CoderState) -> CoderState:
        previous_implementation = self._group_by_component(state["implementation"])
        screens_implementation = previous_implementation["screens_implementation"]
        new_implementation = []

        for component, files in previous_implementation.items():
            if component != "screens_implementation":
                result = self._view_extractor.extract(files["actions"], files["assertions"],screens_implementation)
                screens_implementation = result.get("screens_implementation")
                new_implementation.append(result["actions"])
                new_implementation.append(result["assertions"])
                new_implementation.append(result["view"])

        new_implementation.append(screens_implementation)

        state["implementation"] = new_implementation
        return state

    def code(self, scenario: str, frames: list[ActionFrame]):
        actions = [
            {
                "element_name": frames["element"]["element"]["name"],
                "element_xpath": frames["element"]["element"]["xpath"],
                "element_action": frames["type"],
                "element_action_data": frames.get("data"),
                "screen_description": frames["element"]["element"]["screen_description"],
                "screen_hierarchy": without_fields(frames["element"]["hierarchy"], ["bounds", "index", "package"])
            } for frames in frames
        ]
        result = self._graph.invoke({
            "scenario": scenario,
            "actions": actions
        })
        files: list[UITestsKotlinFile] = result["interfaces"]
        files.extend(result["implementation"])
        return files
