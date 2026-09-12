import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class MemoryManager:
    def __init__(self, char_path, embedding_model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        self.memory_path = os.path.join(char_path, "memory")
        if not os.path.exists(self.memory_path):
            os.makedirs(self.memory_path)

        self.embedding_model = SentenceTransformer(embedding_model_name)

        # Define memory files
        self.memory_files = {
            "user": "user.json",
            "relationship": "relationship.json",
            "events": "events.json",
            "world": "world.json",
            "temporary": "temporary.json",
            "development": "development.json" # specific character development
        }

        self.memories = {}
        self.embeddings = {}

        self._load_memories()

    def _load_memories(self):
        for key, filename in self.memory_files.items():
            file_path = os.path.join(self.memory_path, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.memories[key] = data if isinstance(data, list) else [data]
                except json.JSONDecodeError:
                    self.memories[key] = []
            else:
                self.memories[key] = []
                self._save_memory(key)

        # Build embeddings
        self._build_embeddings()

    def _save_memory(self, key):
        file_path = os.path.join(self.memory_path, self.memory_files[key])
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories[key], f, indent=4, ensure_ascii=False)

    def _build_embeddings(self):
        self.embeddings = {}
        for key, memory_list in self.memories.items():
            if not memory_list:
                self.embeddings[key] = np.array([])
                continue

            # Extract text to embed. Assuming memories are lists of dicts with a 'text' or 'content' field
            texts = []
            for item in memory_list:
                if isinstance(item, dict):
                    texts.append(item.get("text", item.get("content", str(item))))
                else:
                    texts.append(str(item))

            if texts:
                self.embeddings[key] = self.embedding_model.encode(texts)
            else:
                self.embeddings[key] = np.array([])

    def add_memory(self, category, memory_dict, check_similarity=True, threshold=0.85):
        """Adds a memory to a specific category. Checks for similarity if required."""
        if category not in self.memories:
            return False

        memory_text = memory_dict.get("text", memory_dict.get("content", str(memory_dict)))

        if check_similarity and len(self.memories[category]) > 0 and len(self.embeddings[category]) > 0:
            new_embedding = self.embedding_model.encode([memory_text])[0]
            similarities = cosine_similarity([new_embedding], self.embeddings[category])[0]

            if np.max(similarities) > threshold:
                return False # Too similar, skip

        self.memories[category].append(memory_dict)
        self._save_memory(category)

        # Rebuild embeddings for this category
        new_embedding = self.embedding_model.encode([memory_text])
        if len(self.embeddings[category]) > 0:
            self.embeddings[category] = np.vstack([self.embeddings[category], new_embedding])
        else:
            self.embeddings[category] = new_embedding

        return True

    def get_relevant_memories(self, query, top_k=3):
        """Retrieves relevant memories across all categories based on the query."""
        query_embedding = self.embedding_model.encode([query])

        relevant_memories = []
        for category, embeddings in self.embeddings.items():
            if len(embeddings) == 0:
                continue

            similarities = cosine_similarity(query_embedding, embeddings)[0]

            # Get top indices
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            for idx in top_indices:
                if similarities[idx] > 0.3: # Minimum similarity threshold
                    memory_item = self.memories[category][idx]
                    relevant_memories.append({
                        "category": category,
                        "content": memory_item,
                        "score": float(similarities[idx])
                    })

        # Sort combined results by score
        relevant_memories.sort(key=lambda x: x["score"], reverse=True)
        return relevant_memories[:top_k]

    def get_all_memories(self):
        return self.memories

    def update_temporary_state(self, state_dict):
        """Updates temporary state like mood"""
        # Ensure temporary memory is a single dict for state
        if not self.memories["temporary"]:
            self.memories["temporary"] = [state_dict]
        else:
            self.memories["temporary"][0].update(state_dict)
        self._save_memory("temporary")

    def get_temporary_state(self):
        if self.memories["temporary"]:
            return self.memories["temporary"][0]
        return {}
