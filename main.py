import argparse
import typing

import ankiconnect
import reverso


def parse_args():
    parser = argparse.ArgumentParser(description="Translate English words to Russian")
    parser.add_argument("-w", "--word", help="English word to translate")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    r = reverso.get_reverso_result(args.word.strip().lower())
    print(r)
    ans = input("Add to Anki? (y/n): ")
    if ans != "y":
        return
    ankiconnect.add_card_to_anki(r.en_word, r.ru_translations, r.usage_samples)
    ankiconnect.sync()


if __name__ == "__main__":
    main()
