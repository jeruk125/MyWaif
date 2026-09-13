import requests
import urllib.parse
import os
import uuid

EMOTION_PRESETS = {
    "netral": {"speedScale": 1.0, "pitchScale": 0.0, "intonationScale": 1.0, "volumeScale": 1.0},
    "senang": {"speedScale": 1.1, "pitchScale": 0.05, "intonationScale": 1.3, "volumeScale": 1.0},
    "sedih": {"speedScale": 0.9, "pitchScale": -0.05, "intonationScale": 0.8, "volumeScale": 0.9},
    "marah": {"speedScale": 1.15, "pitchScale": 0.0, "intonationScale": 1.4, "volumeScale": 1.2},
    "tsundere": {"speedScale": 1.05, "pitchScale": 0.03, "intonationScale": 1.5, "volumeScale": 1.0},
    "takut": {"speedScale": 1.1, "pitchScale": 0.03, "intonationScale": 1.2, "volumeScale": 0.9},
    "bisik": {"speedScale": 0.95, "pitchScale": -0.02, "intonationScale": 0.7, "volumeScale": 0.6}
}

class VoicevoxClient:
    def __init__(self, base_url, audio_cache_dir="audio_cache"):
        self.base_url = base_url
        self.audio_cache_dir = audio_cache_dir
        if not os.path.exists(self.audio_cache_dir):
            os.makedirs(self.audio_cache_dir)

    def synthesize(self, text, speaker_id=2, emotion="netral", intensity=1.0, style_mapping=None):
        """Generates audio from text using VoiceVox and saves it to a file."""
        if not text:
            return None

        if style_mapping is None:
            style_mapping = {}

        # Override speaker_id if the emotion has a specific style mapping
        if emotion in style_mapping:
            speaker_id = style_mapping[emotion]

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

            # 2. Apply emotion presets via linear interpolation
            target_preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS["netral"])
            base_preset = EMOTION_PRESETS["netral"]

            for key in ["speedScale", "pitchScale", "intonationScale", "volumeScale"]:
                base_val = base_preset[key]
                target_val = target_preset[key]
                # Linear interpolation
                interpolated_val = base_val + (target_val - base_val) * intensity
                query_data[key] = interpolated_val

            # 3. Synthesize audio
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
