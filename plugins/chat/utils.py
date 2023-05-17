from typing import Any

import openai
import tiktoken


def set_api_key(api_key) -> None:
    openai.api_key = api_key


def get_completion(
    system: str, prompt: str, model: str = "gpt-3.5-turbo", temperature: float = 0
) -> str:
    response: Any = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=1024,
        top_p=0,
        frequency_penalty=1,
        presence_penalty=0,
    )
    return response["choices"][0]["message"]["content"]


encoding: tiktoken.Encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


def calc_tokens(prompt: str) -> int:
    return len(encoding.encode(prompt))
