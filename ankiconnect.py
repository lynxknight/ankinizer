import json
import logging
import subprocess
import time
import typing
import urllib.error
import urllib.request

from reverso import ReversoResult, ReversoTranslationSample

TARGET_DECK = "English words"
ANKI_CONNECT_URL = "http://127.0.0.1:8765"
MAX_STARTUP_WAIT_SECONDS = 10

logger = logging.getLogger(__name__)


def is_anki_connect_responding() -> bool:
    """Check if AnkiConnect is responding to requests."""
    try:
        # Try to make a simple request to AnkiConnect
        urllib.request.urlopen(urllib.request.Request(ANKI_CONNECT_URL, json.dumps({
            "action": "version",
            "version": 6
        }).encode('utf-8')))
        logger.info("AnkiConnect is responding")
        return True
    except Exception as e:
        logger.error(f"Error checking AnkiConnect: {e}")
        return False


def launch_anki() -> bool:
    try:
        subprocess.Popen(['open', '/Applications/Anki.app'])
        start_time = time.time()
        while time.time() - start_time < MAX_STARTUP_WAIT_SECONDS:
            if is_anki_connect_responding():
                logger.info("Anki is now running and responding")
                return True
            time.sleep(1)
        logger.error(f"Anki failed to respond within {MAX_STARTUP_WAIT_SECONDS} seconds")
    except Exception as e:
        logger.error(f"Error launching Anki: {e}")
    return False


def ensure_anki_running()
    if is_anki_connect_responding():
        return 
    
    logger.info("Anki is not running, attempting to launch...")
    return launch_anki()


def _invoke(action, **params):
    def request(action, **params):
        return {"action": action, "params": params, "version": 6}

    if not ensure_anki_running():
        raise Exception("Failed to ensure Anki is running")

    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    try:
        response = json.load(
            urllib.request.urlopen(
                urllib.request.Request(ANKI_CONNECT_URL, requestJson)
            )
        )
    except Exception as e:
        raise Exception(f"Failed to communicate with AnkiConnect: {e}")

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
