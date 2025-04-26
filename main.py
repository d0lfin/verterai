import json
import os

from langchain_anthropic import ChatAnthropic

from coder.automator import Automator
from coder.builder import GradleBuildAgent
from explorer.scenario_explorer import ScenarioExplorer
from utils import get_file_content

model = ChatAnthropic(
    model_name="claude-3-7-sonnet-latest",
    # model_name="claude-3-5-haiku-latest",
    api_key=get_file_content(".anthropic_token"),
    temperature=0.0,
    max_tokens=40_000
)

request = """
Enter "example" in the task name field. Click 'Add'. Tap on the task delete button
"""


def launch_agent(record_trace=False):
    if record_trace:
        explorer = ScenarioExplorer(model)
        trace = explorer.explore(request)
        with open("data.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(trace))
    else:
        trace = json.loads(get_file_content("data.json"))

    automator = Automator(model)
    source_code = automator.code(request, trace)

    for code_file in source_code:
        file_path = "example/app/src/androidTest/java/verterai/example/" + code_file.relative_filepath
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_file.source)

    GradleBuildAgent("example/", model).build_and_fix()


if __name__ == '__main__':
    launch_agent(record_trace=False)
