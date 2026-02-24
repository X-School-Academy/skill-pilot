import os
from pinecone import Pinecone
from openai import AsyncOpenAI


class PineconeClient:
    def __init__(self):
        api_key = os.getenv('PINECONE_API_KEY')
        environment = os.getenv('PINECONE_ENVIRONMENT')
        self.index_name = os.getenv('PINECONE_INDEX_NAME')

        self.pc = Pinecone(api_key=api_key, environment=environment)
        self.index = self.pc.Index(self.index_name)
        self.llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL')

    async def get_embedding(self, text):
        try:
            response = await self.llm_client.embeddings.create(
                input=text,
                model=self.embedding_model,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return []

    async def get_messages_hooks(self, text, top_k=5):
        try:
            embedding = await self.get_embedding(text)

            query_response = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )

            rag_messages = []
            for match in query_response['matches']:
                # print(match)
                if match['score'] > 0.45:
                    rag_messages.append( match['metadata'])
            if len(rag_messages) == 0:
                rag_messages.append(query_response['matches'][0]['metadata'])
                
            ref_messages = []
            tools = set()
                
            for msg in rag_messages:
                if any(msg.get(key) for key in ["student", "teacher", "content", "dialog"]):
                    student = msg.get("student")
                    teacher = msg.get("teacher")
                    content = msg.get("content")
                    dialog = msg.get("dialog")
                    hooks = msg.get("hook") or msg.get("hooks")
                    if hooks != 'none' and hooks:
                        if not isinstance(hooks, list):
                            hooks = hooks.split(",")
                        for hook in hooks:
                            tools.add(hook.strip()) 
                    if student and teacher:
                        ref_messages.append(f"Question: {student}\nAnswer: {teacher}")
                    else:
                        ref_messages.append(content or dialog)
                
            return ref_messages, tools
        except Exception as e:
            print(f"Error retrieving messages from Pinecone: {e}")
            return []

    def delete_messages(self, filter_params):
        try:
            self.index.delete(filter=filter_params)
            return True
        except Exception as e:
            print(f"Error deleting messages from Pinecone: {e}")
            return False
