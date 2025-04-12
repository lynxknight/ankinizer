import dataclasses
import itertools
import logging
import typing

import env
import requests

from reverso_agent import get_reverso_result

logger = logging.getLogger(__name__)


# global requests_count
# requests_count = 0

# original_send = requests.Session.send

# def custom_send(self, request: requests.PreparedRequest, **kwargs):
#     global requests_count
#     requests_count += 1
#     logger.info(f"Requests count: {requests_count}")
#     logger.info(f"URL: {request.url}")
#     logger.info(f"Method: {request.method}")
#     logger.info(f"Headers: {request.headers}")
#     logger.info(f"Body: {request.body}")
#     return original_send(self, request, **kwargs)

# requests.Session.send = custom_send

@dataclasses.dataclass
class ReversoTranslationSample:
    en: str
    ru: str

    def __repr__(self) -> str:
        return f"\tReversoTranslationSample<{self.en=}, {self.ru=}>"

    def __str__(self) -> str:
        return f"{self.en} -> {self.ru}"


@dataclasses.dataclass
class ReversoResult:
    en_word: str
    ru_translations: typing.List[str]
    usage_samples: typing.List[ReversoTranslationSample]

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"ReversoResult<{self.en_word=}>:",
                f"{self.ru_translations=}",
                "\n".join(str(sample) for sample in self.usage_samples),
            ]
        )

    def get_usage_samples_html(self) -> str:
        return "\n\n".join(str(sample) for sample in self.usage_samples)

if __name__ == "__main__":
    env.setup_env()
    print(get_reverso_result("test"))
