import anthropic


def get_file_content(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()


def count_tokens(text: str) -> int:
    client = anthropic.Anthropic(
        api_key=get_file_content('.anthropic_token')
    )
    response = client.messages.count_tokens(
        model="claude-3-7-sonnet-20250219",
        messages=[{
            "role": "user",
            "content": text
        }],
    )

    return response.input_tokens