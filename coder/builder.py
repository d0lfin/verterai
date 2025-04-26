import os
import re
import subprocess
from typing import List, Dict, Any, Optional, TypedDict, Literal, Annotated
import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AnyMessage
from langgraph.constants import START
from langgraph.graph import StateGraph, END, add_messages
from langchain_core.tools import tool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from utils import get_file_content


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    build_output: str  # Результат последней сборки
    errors: List[Dict[str, str]]  # Обнаруженные ошибки
    files_examined: List[str]  # Просмотренные файлы
    files_fixed: List[Dict[str, str]]  # Исправленные файлы и описания исправлений
    status: Literal["RUNNING", "FIXED", "MAX_ATTEMPTS_REACHED"]  # Статус работы
    current_error: Optional[Dict[str, str]]  # Текущая обрабатываемая ошибка


class GradleBuildAgent:
    def __init__(self, project_dir: str, model: BaseChatModel):
        self._project_dir = os.path.abspath(project_dir)
        self._model = model
        self.graph = self._create_graph()

    def _create_tools(self):
        @tool
        def run_gradle_compile() -> str:
            """
            Runs './gradlew compileDebugAndroidTestKotlin' in the specified project directory
            and returns the output of the command. Use this tool to run the build
            and get information about compilation errors.
            """
            try:
                os.chdir(self._project_dir)
                result = subprocess.run(
                    ["./gradlew", "compileDebugAndroidTestKotlin"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 минут на выполнение
                )
                return result.stdout + "\n" + result.stderr
            except Exception as e:
                return str(e)

        @tool
        def read_file(file_path: str) -> str:
            """
            Reads the contents of a file. The file path must be relative to the project directory.
            Use this tool to examine the code of files that contain errors.
            """
            try:
                full_path = os.path.join(self._project_dir, file_path)
                with open(full_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except Exception as e:
                return str(e)

        @tool
        def write_file(file_path: str, content: str) -> str:
            """
            Writes content to a file. The file path must be relative to the project directory.
            Use this tool to fix errors in files.
            """
            try:
                full_path = os.path.join(self._project_dir, file_path)
                with open(full_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return f"File {file_path} updated!"
            except Exception as e:
                return str(e)

        @tool
        def list_files(directory: str = "") -> str:
            """
            Returns a list of files in the specified directory (relative to the project root).
            If no directory is specified, returns a list of files in the project root.
            Use this tool to explore the structure of a project.
            """
            try:
                target_dir = os.path.join(self._project_dir, directory)
                files = []
                for item in os.listdir(target_dir):
                    item_path = os.path.join(target_dir, item)
                    if os.path.isdir(item_path):
                        files.append(f"{item}/")
                    else:
                        files.append(item)
                return "\n".join(files)
            except Exception as e:
                str(e)

        return [run_gradle_compile, read_file, write_file, list_files]

    def _create_graph(self) -> CompiledStateGraph:
        tools = self._create_tools()
        self._model = self._model.bind_tools(tools)

        def run_build(state: AgentState) -> AgentState:
            os.chdir(self._project_dir)
            try:
                os.chmod("./gradlew", os.stat("./gradlew").st_mode | 0o111)
                result = subprocess.run(
                    ["./gradlew", "compileDebugAndroidTestKotlin"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout + "\n" + result.stderr
            except Exception as e:
                output = str(e)

            state["build_output"] = output
            state["errors"] = self._parse_build_errors(output)
            simplified_output = _simplify_build_output(output)

            state["messages"].append(
                HumanMessage(
                    content=f"Compilation results:\n\n{simplified_output}\n\n"
                            f"Founded errors: {len(state['errors'])}"
                )
            )

            return state

        def _simplify_build_output(output: str) -> str:
            kotlin_errors = re.findall(r'e: file:///(.*?):\d+:\d+ (.*?)(?:\n|$)', output, re.MULTILINE)
            gradle_failure = re.search(
                r'FAILURE: Build failed with an exception\.\s*\* What went wrong:\s*(.*?)(?:\n\n|\n\*|$)',
                output, re.DOTALL)

            simplified = ""

            if kotlin_errors:
                simplified += "KOTLIN COMPILATION ERRORS:\n"
                for file_path, error_msg in kotlin_errors:
                    simplified += f"- {os.path.basename(file_path)}: {error_msg}\n"
                simplified += "\n"

            if gradle_failure:
                simplified += f"GRADLE ERRORS:\n{gradle_failure.group(1).strip()}\n\n"

            if not simplified:
                if len(output) > 2000:
                    return output[:1000] + "\n...\n" + output[-1000:]
                return output

            return simplified

        def analyze_and_decide(state: AgentState) -> str:
            if "BUILD SUCCESSFUL" in state["build_output"]:
                state["status"] = "FIXED"
                return END

            if state["errors"]:
                state["current_error"] = state["errors"][0]
                return "fix_errors"
            else:
                return END

        def fix_errors(state: AgentState) -> AgentState:
            if state["current_error"]:
                file_path = state["current_error"].get("file", "")
                error_desc = f"The following error needs to be corrected:\n{json.dumps(state['current_error'], indent=2)}"
                state["messages"].append(HumanMessage(content=error_desc))

                if file_path:
                    try:
                        rel_path = os.path.relpath(file_path, self._project_dir) if os.path.isabs(
                            file_path) else file_path
                        full_path = os.path.join(self._project_dir, rel_path)

                        if os.path.exists(full_path):
                            with open(full_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()

                            state["messages"].append(
                                HumanMessage(content=f"File content {rel_path}:\n\n```kotlin\n{file_content}\n```")
                            )
                            state["files_examined"].append(rel_path)
                        else:
                            state["messages"].append(
                                HumanMessage(
                                    content=f"File {rel_path} not found.")
                            )
                    except Exception as e:
                        state["messages"].append(
                            HumanMessage(content=f"Reading problems: {str(e)}")
                        )

            response = self._model.invoke(state["messages"])
            state["messages"].append(response)

            return state

        workflow = StateGraph(AgentState)
        workflow.add_node("run_build", run_build)
        workflow.add_node("analyze_and_decide", analyze_and_decide)
        workflow.add_node("fix_errors", fix_errors)
        workflow.add_node("tools", ToolNode(tools))

        workflow.add_edge(START, "run_build")
        workflow.add_conditional_edges("run_build", analyze_and_decide)
        workflow.add_conditional_edges("fix_errors",
                                       lambda state: "tools" if state["messages"][-1].tool_calls else END)
        workflow.add_edge("tools", "fix_errors")

        return workflow.compile()

    @staticmethod
    def _parse_build_errors(output: str) -> List[Dict[str, str]]:
        errors = []
        kotlin_error_pattern = r'e: file:///(.*?):(\d+):(\d+) (.*?)(?:\n|$)'
        kotlin_matches = re.finditer(kotlin_error_pattern, output, re.MULTILINE)
        for match in kotlin_matches:
            errors.append({
                'file': match.group(1),
                'line': match.group(2),
                'column': match.group(3),
                'message': match.group(4)
            })

        if not errors:
            error_patterns = [
                r'(?:error:|FAILURE:|Error:)\s*(.*?):(\d+):\s*(.*?)(?:\n|$)',
                r'(?:error:|FAILURE:|Error:)\s*(.*?)(?:\n|$)',
            ]

            for pattern in error_patterns:
                matches = re.finditer(pattern, output, re.MULTILINE)
                for match in matches:
                    if len(match.groups()) >= 3:
                        errors.append({
                            'file': match.group(1),
                            'line': match.group(2),
                            'message': match.group(3)
                        })
                    else:
                        errors.append({
                            'message': match.group(1)
                        })

        gradle_failure = re.search(
            r'FAILURE: Build failed with an exception\.\s*\* What went wrong:\s*(.*?)(?:\n\n|\n\*|$)',
            output, re.DOTALL)
        if gradle_failure and not any('Build failed' in err.get('message', '') for err in errors):
            errors.append({
                'message': f"Gradle build failed: {gradle_failure.group(1).strip()}"
            })

        return errors

    def build_and_fix(self) -> Dict[str, Any]:
        initial_state = AgentState(
            messages=[SystemMessage(get_file_content("./coder/prompts/fix_build.md"))],
            build_output="",
            errors=[],
            files_examined=[],
            files_fixed=[],
            status="RUNNING",
            current_error=None
        )

        return self.graph.invoke(
            initial_state,
            {
                "recursion_limit": 100
            }
        )
