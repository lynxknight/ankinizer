import json
import typing
import urllib.request

from reverso import ReversoResult, ReversoTranslationSample

TARGET_DECK = "English words"


def _invoke(action, **params):
    def request(action, **params):
        return {"action": action, "params": params, "version": 6}

    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        raise Exception(response["error"])
    return response["result"]


def add_card_to_anki(
    reverso_result: ReversoResult,
    sync=False,
):
    rr = reverso_result
    back = (
        " / ".join(rr.ru_translations)
        + "<br><br> * "
        + "<br> * ".join(map(str, rr.usage_samples))
    )
    note = {
        "deckName": TARGET_DECK,
        "modelName": "Basic",
        "fields": {"Front": rr.en_word, "Back": back},
        "tags": ["ankinizer"],
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
        },
    }
    try:
        _invoke("addNote", note=note)
    except Exception as e:
        if "duplicate" in str(e):
            print("card already exists")
            return
        else:
            raise
    print("card added")
    if sync:
        _invoke("sync")


def sync():
    _invoke("sync")
    print("synced")


def _main():
    result = _invoke("deckNames")
    print("got list of decks: {}".format(result))


if __name__ == "__main__":
    _main()
