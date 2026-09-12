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

        return {
            "id": character_id,
            "persona": persona,
            "lore": lore,
            "path": char_path
        }
