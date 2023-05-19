import asyncio

import markdownify
import openai
import tiktoken
from loguru import logger
from playwright.async_api import async_playwright
from .prompts import summary, translate
from readability import Document

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
max_tokens = 1024


def calc_tokens(prompt: str) -> int:
    tokens = encoding.encode(prompt)
    return len(tokens)


async def get_completion(prompt, temperature=0) -> str:
    logger.debug(f"[OpenAI] Prompt:\n{prompt}")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=temperature,
    )
    text = response["choices"][0]["message"]["content"]  # type: ignore
    logger.debug(f"[OpenAI] Response: {text}")
    return text


def filter_type(route):
    return (
        route.abort()
        if route.request.resource_type in ["image", "font", "ping"]
        else route.continue_()
    )


class Assistant:
    def __init__(self, language) -> None:
        self._language = language

    async def _get_summary(self, paragraph_list: list[str]) -> str:
        if len(paragraph_list) <= 2:
            prompt = summary.format(text="\n".join(paragraph_list))
            return await get_completion(prompt)

        mid = len(paragraph_list) // 2
        left = paragraph_list[:mid]
        right = paragraph_list[mid:]

        left_summary, right_summary = await asyncio.gather(
            self._get_summary(left),
            self._get_summary(right),
        )

        return await self._get_summary([left_summary, right_summary])

    async def _fetch(self, url) -> str:
        logger.info(f"Fetching {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.route("*", filter_type)
            await page.goto(url)
            await page.wait_for_timeout(1000)
            html = await page.content()
            await browser.close()
            return html

    def _parse_content(self, html) -> str:
        doc = Document(html)
        main_content = markdownify.markdownify(doc.summary(), heading_style="ATX")
        if not main_content:
            raise Exception("No content")
        return main_content

    def _split_long_content(self, content: str) -> list[str]:
        results = []
        ps = content.split("\n")
        for p in ps:
            if not results:
                results.append(p)
                continue
            prompt = summary.format(text=results[-1] + "\n" + p)
            if calc_tokens(prompt) > max_tokens:
                results.append(p)
            else:
                results[-1] += "\n" + p
        return results

    async def summarize(self, text: str) -> str:
        paragraph_list = self._split_long_content(text)
        return await self._get_summary(paragraph_list)

    async def summarize_from_url(self, url) -> str:
        try:
            html = await self._fetch(url)
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise e

        summary = await self.summarize(self._parse_content(html))
        prompt = translate.format(language=self._language, text=summary)
        result = await get_completion(prompt)
        return result


assistant = Assistant("Chinese")
