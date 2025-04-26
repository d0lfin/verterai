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

    automator = Automator(model, "example/")
    automator.code(request, trace)

    GradleBuildAgent("example/", model).build_and_fix()


if __name__ == '__main__':
    launch_agent(record_trace=False)
