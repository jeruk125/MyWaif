import requests
import json
import argparse

def get_speakers(base_url="http://127.0.0.1:50021"):
    try:
        response = requests.get(f"{base_url}/speakers")
        response.raise_for_status()
        speakers = response.json()

        print("VoiceVox Available Speakers and Styles:")
        print("-" * 50)

        for speaker in speakers:
            name = speaker.get("name", "Unknown")
            speaker_uuid = speaker.get("speaker_uuid", "")
            print(f"\nSpeaker: {name} (UUID: {speaker_uuid})")

            styles = speaker.get("styles", [])
            for style in styles:
                style_name = style.get("name", "Unknown")
                speaker_id = style.get("id")
                print(f"  - Style: {style_name:<20} | speaker_id: {speaker_id}")

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to VoiceVox at {base_url}: {e}")
        print("Make sure the VoiceVox engine is running.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and list VoiceVox speakers and their styles.")
    parser.add_argument("--url", default="http://127.0.0.1:50021", help="Base URL of the VoiceVox engine (default: http://127.0.0.1:50021)")
    args = parser.parse_args()

    get_speakers(args.url)
