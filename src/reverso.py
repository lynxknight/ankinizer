import dataclasses
import itertools
import typing

import reverso_context_api


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


def get_reverso_result(word) -> ReversoResult:
    client = reverso_context_api.Client("en", "ru")

    def transform_samples(
        samples: typing.List[typing.Tuple[str, str]]
    ) -> typing.List[ReversoTranslationSample]:
        f = lambda x: x.replace("<em>", "<b>").replace("</em>", "</b>")
        return [ReversoTranslationSample(*map(f, example)) for example in samples]

    ru_translations = list(client.get_translations(word))
    raw_usage_samples = list(
        itertools.islice(client.get_translation_samples(word, cleanup=False), 3)
    )
    usage_samples = transform_samples(raw_usage_samples)
    return ReversoResult(
        en_word=word, ru_translations=ru_translations, usage_samples=usage_samples
    ) 