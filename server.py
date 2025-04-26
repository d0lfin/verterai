import os
from time import sleep

import uiautomator2
from langchain_anthropic import ChatAnthropic
from mcp.server.fastmcp import FastMCP
from uiautomator2 import XPathElementNotFoundError

from explorer.element_navigator import ElementNavigator


class ElementNotFoundException(Exception):
    def __init__(self, message, context_data):
        super().__init__(message)
        self.context_data = context_data


mcp = FastMCP("Emulator clicker")
model = ChatAnthropic(
    model_name="claude-3-5-haiku-latest",
    api_key=os.getenv('API_KEY')
)


def click_on(device: uiautomator2.Device, screen_element_description: str) -> dict[str]:
    element_navigator = ElementNavigator(model, device)
    element_info = element_navigator.find_element_info(screen_element_description)

    if element_info.get("element"):
        try:
            device.xpath(element_info["xpath"]).click()
            return element_info
        except XPathElementNotFoundError:
            raise ElementNotFoundException(
                f"'{screen_element_description}' not found by {element_info["xpath"]}",
                context_data=element_info)
    else:
        raise ElementNotFoundException(
            f"'{screen_element_description}' not found by {element_info["xpath"]}",
            context_data=element_info)


@mcp.tool()
def click_on_element_with_description(screen_element_description: str) -> dict[str]:
    """Click on element with description"""
    device = uiautomator2.connect()
    try:
        return click_on(device, screen_element_description)
    finally:
        device.stop_uiautomator()


@mcp.tool()
def input_text_at_element_with_description(screen_element_description: str, text_for_input: str):
    """Input text at element with description"""
    device = uiautomator2.connect()
    try:
        click_on_element_with_description(screen_element_description)
        sleep(3)
        device.send_keys(text_for_input)
    finally:
        device.stop_uiautomator()


if __name__ == "__main__":
    mcp.run(transport="stdio")
