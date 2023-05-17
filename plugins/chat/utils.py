from typing import Any

import openai
import tiktoken

encoding: tiktoken.Encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


async def get_completion(
    prompt: str, model: str = "gpt-3.5-turbo", temperature: float = 0
) -> str:
    response: Any = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=1024,
        top_p=0,
        frequency_penalty=0.5,
        presence_penalty=0.1,
    )
    return response["choices"][0]["message"]["content"]


async def calc_tokens(prompt: str) -> int:
    return len(encoding.encode(prompt))
