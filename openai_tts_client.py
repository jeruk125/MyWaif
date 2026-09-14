import os
import uuid
from openai import OpenAI

class OpenAICompatibleTTSClient:
    def __init__(self, base_url, api_key, model_name, voice, audio_cache_dir="audio_cache"):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.voice = voice
        self.audio_cache_dir = audio_cache_dir

        if not os.path.exists(self.audio_cache_dir):
            os.makedirs(self.audio_cache_dir)

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def synthesize(self, text, speaker_id=None, voice=None):
        """Generates audio from text using OpenAI-compatible API and saves it to a file."""
        if not text:
            return None

        try:
            target_voice = voice if voice else self.voice
            response = self.client.audio.speech.create(
                model=self.model_name,
                voice=target_voice,
                input=text,
                response_format="mp3"
            )

            filename = f"audio_{uuid.uuid4().hex}.mp3"
            filepath = os.path.join(self.audio_cache_dir, filename)

            response.stream_to_file(filepath)

            return filename
        except Exception as e:
            print(f"Error communicating with OpenAI-compatible TTS: {e}")
            return None

    def cleanup_cache(self, keep_latest=50):
        """Removes old audio files to prevent unlimited disk usage."""
        try:
            files = [
                os.path.join(self.audio_cache_dir, f)
                for f in os.listdir(self.audio_cache_dir)
                if f.endswith('.mp3') or f.endswith('.wav')
            ]
            files.sort(key=os.path.getctime)

            # Keep the latest files, delete the rest
            if len(files) > keep_latest:
                for file_to_delete in files[:-keep_latest]:
                    os.remove(file_to_delete)
        except Exception as e:
            print(f"Error cleaning up audio cache: {e}")
