import logging
from typing import List, Dict, Any, Optional
import ollama
import chromadb
from chromadb.utils import embedding_functions
from pydantic import BaseSettings
import asyncio
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotConfig(BaseSettings):
    """Chatbot configuration"""
    MODEL_NAME: str = "gemma2:9b"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    COLLECTION_NAME: str = "company_knowledge"
    MAX_HISTORY_LENGTH: int = 10
    CONTEXT_LENGTH: int = 3  # Reduced to match number of documents

    class Config:
        env_prefix = "CHATBOT_"

class KnowledgeBase:
    """Knowledge base management using ChromaDB"""

    def __init__(self, persist_directory: str, collection_name: str):
        self.client = chromadb.Client(chromadb.Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction()
        
        # Recreate collection each time to ensure fresh start
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass
            
        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        
        logger.info("Knowledge base initialized successfully")

    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to knowledge base"""
        try:
            texts = [doc["text"] for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            ids = [doc["metadata"]["source"] for doc in documents]  # Use filename as ID
            
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents with metadata"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            for i in range(len(results['documents'][0])):
                documents.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'source': results['ids'][0][i]
                })
                
            logger.info(f"Found {len(documents)} documents for query: '{query}'")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise

def load_knowledge_files(directory: str = "knowledge") -> List[Dict[str, Any]]:
    """Load knowledge from txt files"""
    documents = []
    
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory {directory}")
        return documents
    
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                    documents.append({
                        "text": text,
                        "metadata": {
                            "source": filename,
                            "category": filename.replace(".txt", "")
                        }
                    })
                logger.info(f"Loaded file: {filename}")
            except Exception as e:
                logger.error(f"Error reading file {filename}: {str(e)}")
    
    return documents

class Chatbot:
    """Main chatbot class"""

    def __init__(self, config: Optional[ChatbotConfig] = None):
        self.config = config or ChatbotConfig()
        self.client = ollama.Client()
        
        # Initialize knowledge base
        self.knowledge_base = KnowledgeBase(
            self.config.KNOWLEDGE_BASE_DIR,
            self.config.COLLECTION_NAME
        )
        
        self.conversation_history: List[Dict[str, str]] = []

    def add_knowledge(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to knowledge base"""
        return self.knowledge_base.add_documents(documents)

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process user message"""
        try:
            logger.info(f"Received user message: '{message}'")
            
            # Search for relevant context
            context_docs = self.knowledge_base.search(
                message, 
                n_results=self.config.CONTEXT_LENGTH
            )
            
            # Format context with source information
            context_text = "\n\n".join([
                f"From {doc['source']}:\n{doc['text']}" 
                for doc in context_docs
            ])
            
            # Prepare system prompt
            system_prompt = f"""You are a professional and helpful company assistant focused on providing accurate customer service. Your responses should be based EXCLUSIVELY on the provided company knowledge base.
            
Role and Personality:
- Professional, friendly, and concise in communication
- Patient and understanding with customers
- Focused on providing accurate, helpful information
- Natural conversational style while maintaining professionalism

Response Guidelines:
1. Knowledge Base Usage:
    - Use ONLY information from the provided context
    - Do not invent, assume, or extrapolate information
    - If information is not in the context, clearly state: "I don't have this information in my knowledge base"
    
2. Response Structure:
    - Start with a direct answer to the question
    - Provide relevant details from the context if available
    - Keep responses concise and to the point
    - Use natural, conversational language
    
3. Interaction Rules:
    - Don't reference the source of your information
    - Don't apologize for limitations
    - Don't make promises or commitments
    - Stay within the scope of provided information
    
Available information:
{context_text}

Example Responses:
Q: "What are your working hours?"
A: "We're open Monday to Friday, 9 AM to 6 PM."

Q: "Do you offer international shipping?"
A: "I don't have this information in my knowledge base."

Remember: Always prioritize accuracy over comprehensiveness. If unsure, acknowledge the limitations of the available information.
"""

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history,
                {"role": "user", "content": message}
            ]
            
            # Get model response
            response = self.client.chat(
                model=self.config.MODEL_NAME,
                messages=messages
            )
            
            assistant_response = response['message']['content']
            
            # Update conversation history
            self.conversation_history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_response}
            ])
            
            # Limit history length
            if len(self.conversation_history) > self.config.MAX_HISTORY_LENGTH:
                self.conversation_history = self.conversation_history[-self.config.MAX_HISTORY_LENGTH:]
            
            return {
                "status": "success",
                "response": assistant_response,
                "sources": [doc['source'] for doc in context_docs]
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

async def main():
    # Initialize bot
    bot = Chatbot()
    
    # Load knowledge files
    documents = load_knowledge_files()
    if documents:
        bot.add_knowledge(documents)
    else:
        logger.warning("No knowledge files found in knowledge directory")
    
    print("\nChatbot is ready. Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("You: ")
            
            if user_input.lower() in ['выход', 'exit', 'quit']:
                print("Goodbye!")
                break
            
            response = await bot.process_message(user_input)
            
            if response["status"] == "success":
                print(f"\nBot: {response['response']}")
                print(f"Sources used: {', '.join(response['sources'])}\n")
            else:
                print(f"\nError: {response['error']}\n")
                
        except KeyboardInterrupt:
            print("\nOperation terminated")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(main())
