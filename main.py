import argparse
import dataclasses
import itertools
import typing

import ankiconnect

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


def get_reverso_result(word) -> ReversoResult:
    client = reverso_context_api.Client("en", "ru")

    def transform_samples(
        samples: typing.List[typing.Tuple[str, str]]
    ) -> typing.List[ReversoTranslationSample]:
        f = lambda x: x.replace("<em>", "<b>").replace("</em>", "</b>")
        return [ReversoTranslationSample(*map(f, example)) for example in samples]

    return ReversoResult(
        en_word=word,
        ru_translations=list(client.get_translations(word)),
        usage_samples=transform_samples(
            list(
                itertools.islice(client.get_translation_samples(word, cleanup=False), 3)
            )
        ),
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Translate English words to Russian")
    parser.add_argument("-w", "--word", help="English word to translate")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    r = get_reverso_result(args.word.strip().lower())
    print(r)
    ans = input("Add to Anki? (y/n): ")
    if ans != "y":
        return
    ankiconnect.add_card_to_anki(r.en_word, r.ru_translations, r.usage_samples)
    ankiconnect.sync()


if __name__ == "__main__":
    main()
