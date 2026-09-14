import json
import os

class CharacterLoader:
    def __init__(self, base_path="characters"):
        self.base_path = base_path

    def load_character(self, character_id):
        char_path = os.path.join(self.base_path, character_id)
        if not os.path.exists(char_path):
            raise ValueError(f"Character {character_id} not found.")

        # Load character.txt
        char_txt_path = os.path.join(char_path, "character.txt")
        persona = ""
        if os.path.exists(char_txt_path):
            with open(char_txt_path, "r", encoding="utf-8") as f:
                persona = f.read()

        # Load lore.txt
        lore_txt_path = os.path.join(char_path, "lore.txt")
        lore = ""
        if os.path.exists(lore_txt_path):
            with open(lore_txt_path, "r", encoding="utf-8") as f:
                lore = f.read()

        # Parse speaker_id and voice_openai
        import re
        speaker_id = 2 # Default VoiceVox speaker
        m_speaker = re.search(r'Speaker ID VoiceVox:\s*(\d+)', persona, re.IGNORECASE)
        if m_speaker:
            speaker_id = int(m_speaker.group(1))

        voice_openai = None
        m_voice = re.search(r'voice_openai:\s*(.+)', persona, re.IGNORECASE)
        if m_voice:
            voice_openai = m_voice.group(1).strip()

        return {
            "id": character_id,
            "persona": persona,
            "lore": lore,
            "path": char_path,
            "speaker_id": speaker_id,
            "voice_openai": voice_openai
        }
