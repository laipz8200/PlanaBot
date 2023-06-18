import re
from typing import Any

import httpx
import readability
import tiktoken
from langchain import LLMChain, PromptTemplate
from langchain.chains import SequentialChain
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownTextSplitter
from markdownify import markdownify

from plana import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage

from .prompts import translate_template

encoding: tiktoken.Encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


def tiktoken_len(prompt: str) -> int:
    tokens = encoding.encode(prompt)
    return len(tokens)


text_splitter = MarkdownTextSplitter(
    chunk_size=1024 * 10,
    chunk_overlap=0,
    length_function=tiktoken_len,
)


class TLDR(Plugin):
    prefix: str = "#tldr"
    openai_api_key: str
    chain: Any | SequentialChain = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        llm = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0.0,
            openai_api_key=self.openai_api_key,
        )  # type: ignore

        summarize_chain = load_summarize_chain(
            llm,
            chain_type="map_reduce",
            output_key="text",
            verbose=True,
        )
        translate_chain = LLMChain(
            llm=llm,
            prompt=PromptTemplate.from_template(translate_template),
            output_key="translated_text",
            verbose=True,
        )

        self.chain = SequentialChain(
            chains=[summarize_chain, translate_chain],
            input_variables=["input_documents", "language"],
            output_variables=["text", "translated_text"],
        )

    async def _summarize(self, message: BaseMessage) -> None:
        if self.chain is None:
            await message.reply("老师, 总结模块异常, 请等我检查一下")
            return

        command = message.plain_text()
        # 判断command是不是合法 url
        if not re.match(r"^https?://.*", command):
            await message.reply("老师, 请输入正确的网络地址")
            return

        try:
            await message.reply(f"Plana 开始尝试访问 {command}")
            response = httpx.get(
                command,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"  # noqa: E501
                },
            )
            if response.status_code != httpx.codes.OK:
                await message.reply(
                    f"老师, 网站返回了 {response.status_code} 状态码, 内容是 {response.text}"  # noqa: E501
                )
                return
            doc = readability.Document(response.text)
            markdown = markdownify(doc.summary(), heading_style="ATX")
            if not markdown.split():
                await message.reply("老师, 没有获取到内容")
                return

            chunks = text_splitter.split_text(markdown)
            docs = [Document(page_content=chunk) for chunk in chunks]

            await message.reply("正在阅读并总结内容...")
            result = await self.chain.acall(
                {"input_documents": docs, "language": "Chinese"}
            )
            await message.reply(f'老师, 这是你需要的结果:\n{result["translated_text"]}')
        except Exception as e:
            await message.reply(f"老师, 遇到了错误: {e}")

    async def on_private_prefix(self, message: PrivateMessage) -> None:
        await self._summarize(message)

    async def on_group_prefix(self, message: GroupMessage) -> None:
        await self._summarize(message)
