import requests
import urllib.parse
import os
import uuid

class VoicevoxClient:
    def __init__(self, base_url, audio_cache_dir="audio_cache"):
        self.base_url = base_url
        self.audio_cache_dir = audio_cache_dir
        if not os.path.exists(self.audio_cache_dir):
            os.makedirs(self.audio_cache_dir)

    def synthesize(self, text, speaker_id=2):
        """Generates audio from text using VoiceVox and saves it to a file."""
        if not text:
            return None

        try:
            # 1. Create audio query
            query_url = f"{self.base_url}/audio_query"
            params = {
                "text": text,
                "speaker": speaker_id
            }
            query_response = requests.post(query_url, params=params, timeout=10)
            query_response.raise_for_status()
            query_data = query_response.json()

            # 2. Synthesize audio
            synth_url = f"{self.base_url}/synthesis"
            synth_params = {
                "speaker": speaker_id
            }
            synth_response = requests.post(
                synth_url,
                params=synth_params,
                json=query_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            synth_response.raise_for_status()

            # 3. Save to file
            filename = f"audio_{uuid.uuid4().hex}.wav"
            filepath = os.path.join(self.audio_cache_dir, filename)

            with open(filepath, "wb") as f:
                f.write(synth_response.content)

            return filename

        except Exception as e:
            print(f"Error communicating with VoiceVox: {e}")
            return None

    def cleanup_cache(self, keep_latest=50):
        """Removes old audio files to prevent unlimited disk usage."""
        try:
            files = [os.path.join(self.audio_cache_dir, f) for f in os.listdir(self.audio_cache_dir) if f.endswith('.wav')]
            files.sort(key=os.path.getctime)

            # Keep the latest files, delete the rest
            if len(files) > keep_latest:
                for file_to_delete in files[:-keep_latest]:
                    os.remove(file_to_delete)
        except Exception as e:
            print(f"Error cleaning up audio cache: {e}")
