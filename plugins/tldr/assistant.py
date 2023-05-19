import markdownify
import openai
import tiktoken
from loguru import logger
from playwright.async_api import async_playwright
from readability import Document

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
max_tokens = 3072


class Assistant:
    def __init__(self, language: str, api_key: str) -> None:
        openai.api_key = api_key
        self._language = language
        self._prompt = """Summarized the following text in {language} in triple backticks by 1 sentence.
Text:
```{text}```"""  # noqa: E501

    def _get_summary(self, paragraph_list, summary="") -> str:
        if paragraph_list:
            paragraph = paragraph_list.pop(0)
            if not summary:
                summary = self._get_completion(self._build_prompt(paragraph))
            else:
                summary = self._get_completion(
                    self._build_prompt(summary + "\n" + paragraph)
                )
            return self._get_summary(paragraph_list, summary)
        return summary

    def _build_prompt(self, prompt: str) -> str:
        return self._prompt.format(language=self._language, text=prompt)

    async def _fetch(self, url):
        logger.info(f"Fetching {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"  # noqa: E501
            )
            page = await context.new_page()

            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ["image", "font", "ping"]
                else route.continue_(),
            )

            await page.goto(url)
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
            if not results or (
                self._get_tokens(text=results[-1] + "\n" + p) > max_tokens
            ):
                results.append(p)
            else:
                results[-1] += "\n" + p
        return results

    def _get_tokens(self, text) -> int:
        prompt = self._prompt.format(language=self._language, text=text)
        tokens = encoding.encode(prompt)
        return len(tokens)

    def _get_completion(self, prompt, temperature=0) -> str:
        logger.debug(f"[OpenAI] Prompt:\n{prompt}")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=temperature,
        )
        text = response["choices"][0]["message"]["content"]  # type: ignore
        logger.debug(f"[OpenAI] Response: {text}")
        return text

    def summarize(self, text: str) -> str:
        paragraph_list = self._split_long_content(text)
        return self._get_summary(paragraph_list)

    async def summarize_from_url(self, url):
        try:
            html = await self._fetch(url)
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise e

        return self.summarize(self._parse_content(html))
