# knowledge_loader.py
import os
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class KnowledgeLoader:
    """Loader for knowledge from text files"""
    
    @staticmethod
    def load_from_txt(filepath: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Load knowledge from a text file
        
        Args:
            filepath: Path to the file
            chunk_size: Size of one text chunk
            
        Returns:
            List[Dict[str, Any]]: List of documents for the knowledge base
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                text = file.read()
            
            # Split the text into parts considering paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            # Combine small paragraphs
            chunks = []
            current_chunk = ""
            
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) <= chunk_size:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Create documents
            documents = [
                {
                    "text": chunk,
                    "metadata": {
                        "source": os.path.basename(filepath),
                        "chunk_id": i
                    }
                }
                for i, chunk in enumerate(chunks)
            ]
            
            logger.info(f"Loaded {len(documents)} documents from {filepath}")
            return documents
                
        except Exception as e:
            logger.error(f"Error loading file {filepath}: {str(e)}")
            raise

class KnowledgeManager:
    """Knowledge base manager for small businesses"""
    
    def __init__(self, chatbot):
        self.chatbot = chatbot
        self.loader = KnowledgeLoader()
    
    def load_knowledge_directory(self, directory: str) -> None:
        """
        Load all .txt files from a directory
        
        Args:
            directory: Path to the knowledge directory
        """
        try:
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    filepath = os.path.join(directory, filename)
                    documents = self.loader.load_from_txt(filepath)
                    self.chatbot.add_knowledge(documents)
                        
            logger.info(f"All files from {directory} have been successfully loaded")
                
        except Exception as e:
            logger.error(f"Error loading directory {directory}: {str(e)}")
            raise

# knowledge_format.txt - example structure of a knowledge file:
"""
# General Information
Our company "Example" has been operating in the market since 2010.
We specialize in selling electronics and household appliances.

# Working Hours
The store is open daily from 9:00 AM to 9:00 PM without breaks or days off.
Technical support is available on weekdays from 8:00 AM to 8:00 PM.

# Delivery
Delivery is carried out throughout the city within 1-2 business days.
Delivery cost depends on the area and ranges from 300 to 500 rubles.
"""

# Example usage:
if __name__ == "__main__":
    import asyncio  # Make sure to import asyncio
    # Assuming Chatbot class is defined elsewhere

    async def main():
        # Initialize the bot
        bot = Chatbot()
        
        # Create the knowledge manager
        knowledge_manager = KnowledgeManager(bot)
        
        # Load knowledge from the directory
        try:
            knowledge_manager.load_knowledge_directory("./knowledge")
        except Exception as e:
            logger.error(f"Error loading knowledge: {str(e)}")
            return
        
        # Test query
        response = await bot.process_message("When is the store open?")
        print(f"Response: {response['response']}")
    
    asyncio.run(main())
