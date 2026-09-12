import json
import requests
import re

class LLMClient:
    def __init__(self, config_providers):
        self.providers = config_providers

    def _call_openai_format(self, provider_config, messages, system_prompt=None, temperature=0.7, json_format=False):
        url = f"{provider_config['base_url']}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider_config['api_key']}"
        }

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": provider_config['model_name'],
            "messages": payload_messages,
            "temperature": temperature
        }

        if json_format:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling OpenAI-format API: {e}")
            return None

    def _call_gemini_format(self, provider_config, messages, system_prompt=None, temperature=0.7):
        # Extremely simplified Gemini REST API call
        # Requires valid gemini API key and correct endpoint structure
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider_config['model_name']}:generateContent?key={provider_config['api_key']}"
        headers = {
            "Content-Type": "application/json"
        }

        # Format messages for Gemini
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None

    def _generate(self, task_type, messages, system_prompt=None, temperature=0.7, json_format=False):
        provider_config = self.providers.get(task_type)
        if not provider_config:
            raise ValueError(f"Provider configuration for '{task_type}' not found.")

        p_type = provider_config.get("type", "local")

        if p_type == "local" or p_type == "openai":
            return self._call_openai_format(provider_config, messages, system_prompt, temperature, json_format)
        elif p_type == "gemini":
            return self._call_gemini_format(provider_config, messages, system_prompt, temperature)
        else:
            raise ValueError(f"Unsupported provider type: {p_type}")

    def generate_chat(self, messages, system_prompt):
        """Generates the main roleplay response."""
        return self._generate("chat", messages, system_prompt=system_prompt, temperature=0.8)

    def translate_to_japanese(self, indonesian_text):
        """Translates text from Indonesian to Japanese for VoiceVox."""
        system_prompt = "You are a professional translator. Translate the following Indonesian text to Japanese. Only output the Japanese text, without any explanations or additional formatting."
        messages = [{"role": "user", "content": indonesian_text}]
        return self._generate("translation", messages, system_prompt=system_prompt, temperature=0.3)

    def extract_memory(self, conversation_log):
        """Extracts facts, relationship updates, etc., from the conversation log."""
        system_prompt = """
        Analyze the provided conversation log. Extract any NEW facts about the user, new events, relationship developments, or world lore that was established.
        Return the extraction in the following JSON format strictly:
        {
            "user": [{"text": "new fact about user"}],
            "relationship": [{"text": "new relationship milestone/promise"}],
            "events": [{"text": "summary of significant event"}],
            "world": [{"text": "new world lore established"}]
        }
        If there is no new information for a category, leave the list empty [].
        Do not include existing or obvious information, only new developments.
        """

        messages = [{"role": "user", "content": f"Conversation Log:\n{conversation_log}"}]

        response = self._generate("memory", messages, system_prompt=system_prompt, temperature=0.1, json_format=True)

        try:
            # Attempt to parse as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback regex extraction if the model didn't output pure JSON
            print("Warning: Failed to parse memory extraction as JSON. Attempting regex.")
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return {"user": [], "relationship": [], "events": [], "world": []}

    def extract_dialogue(self, full_response):
        """Extracts spoken dialogue from a response containing both action and dialogue."""
        # Finds text inside double quotes.
        # Assumes dialogue is wrapped in "..."
        dialogues = re.findall(r'"([^"]*)"', full_response)
        if dialogues:
            return " ".join(dialogues)

        # If no quotes found, try to strip asterisks (actions) and return the rest
        clean_text = re.sub(r'\*[^*]*\*', '', full_response).strip()
        if clean_text:
            return clean_text

        return full_response # Fallback
