import json
import os
import time

from gtts import gTTS
from gtts.tts import gTTSError


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_PATH = os.path.join(BASE_DIR, "schemes.json")
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")

# Retry settings (tune as needed)
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 2


def load_schemes():
    with open(SCHEMES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_voice_text(name: str, data: dict) -> str:
    return (
        f"{name} పథకానికి సంబంధించిన వివరాలు. "
        f"ఈ పథకం అర్హతలు: {data['eligibility_te']}. "
        f"ప్రధాన ప్రయోజనాలు: {data['benefits_te']}. "
        f"అవసరమైన పత్రాలు: {data['documents_te']}. "
        f"దరఖాస్తు చేయాల్సిన దశలు: {data['steps_te']}.")


def generate_audio_for_scheme(name: str, data: dict) -> None:
    audio_path_rel = data["audio_file"]
    audio_path_abs = os.path.join(BASE_DIR, audio_path_rel)

    # Skip if already exists
    if os.path.exists(audio_path_abs) and os.path.getsize(audio_path_abs) > 0:
        print(f"⏭️  Skipping (already exists): {audio_path_rel}")
        return

    voice_text = build_voice_text(name, data)

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tts = gTTS(text=voice_text, lang="te", slow=False)
            # Ensure directory exists
            os.makedirs(os.path.dirname(audio_path_abs), exist_ok=True)
            tts.save(audio_path_abs)
            print(f"✅ Generated: {audio_path_rel}")
            return
        except (gTTSError, Exception) as e:
            last_err = e
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"⚠️  Failed generating {name} (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    # If we got here, all attempts failed
    raise RuntimeError(f"Failed to generate audio for '{name}' after {MAX_RETRIES} attempts: {last_err}")


def main():
    schemes = load_schemes()
    os.makedirs(AUDIO_DIR, exist_ok=True)

    ok = 0
    failed = 0

    for name, data in schemes.items():
        try:
            generate_audio_for_scheme(name, data)
            ok += 1
        except Exception as e:
            failed += 1
            print(f"❌ Giving up on: {name}. Error: {e}")

    print(f"🎉 Done. Success: {ok}, Failed: {failed}")


if __name__ == "__main__":
    main()

