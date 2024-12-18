# server.py
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import logging
from typing import Dict, Any, List
from chatbot import Chatbot

# Set environment variable for tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI instance
app = FastAPI()

# Create required directories
os.makedirs("templates", exist_ok=True)
os.makedirs("knowledge", exist_ok=True)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    text: str

def load_knowledge_files() -> List[Dict[str, Any]]:
    """Load all .txt files from the knowledge directory"""
    documents = []
    knowledge_dir = "knowledge"
    
    # Create example file if directory is empty
    if not os.listdir(knowledge_dir):
        example_file = os.path.join(knowledge_dir, "example.txt")
        with open(example_file, "w", encoding="utf-8") as f:
            f.write(""" """)
        logger.info(f"Created example file: {example_file}")
    
    # Load all .txt files
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(knowledge_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
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

# Create HTML template if it doesn't exist
def create_template():
    template_path = "templates/index.html"
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Chat with Assistant</title>
    <style>
        .chat-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 350px;
            height: 500px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            font-family: Arial, sans-serif;
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .chat-widget.minimized {
            height: 60px;
        }

        .chat-header {
            background: #2c3e50;
            color: white;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }

        .chat-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .message {
            max-width: 80%;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 5px 0;
            word-wrap: break-word;
        }

        .user-message {
            background: #e8f4ff;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }

        .bot-message {
            background: #f0f0f0;
            margin-right: auto;
            border-bottom-left-radius: 5px;
        }

        .chat-input {
            padding: 15px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
        }

        .chat-input input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            outline: none;
        }

        .chat-input button {
            padding: 10px 20px;
            background: #2c3e50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .chat-input button:hover {
            background: #34495e;
        }

        .sources {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div id="chat-widget" class="chat-widget">
        <div class="chat-header" onclick="toggleChat()">
            <span>Assistant</span>
            <span class="minimize">_</span>
        </div>
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input">
            <input type="text" id="chat-input" placeholder="Enter your message..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const CHAT_API_URL = '/chat';
        
        function toggleChat() {
            const widget = document.getElementById('chat-widget');
            widget.classList.toggle('minimized');
        }

        function appendMessage(text, isUser, sources = []) {
            const messagesDiv = document.getElementById('chat-messages');
            const messageContainer = document.createElement('div');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            messageDiv.textContent = text;
            messageContainer.appendChild(messageDiv);
            
            if (!isUser && sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.textContent = `Sources: ${sources.join(', ')}`;
                messageContainer.appendChild(sourcesDiv);
            }
            
            messagesDiv.appendChild(messageContainer);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            appendMessage(message, true);
            input.value = '';

            try {
                const response = await fetch(CHAT_API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ text: message })
                });

                const data = await response.json();
                
                if (data.status === 'success') {
                    appendMessage(data.response, false, data.sources);
                } else {
                    appendMessage('Sorry, an error occurred. Please try again later.', false);
                }
            } catch (error) {
                console.error('Error:', error);
                appendMessage('Sorry, an error occurred. Please try again later.', false);
            }
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
    </script>
</body>
</html>""")
        logger.info("Created index.html template")

# Global variable for bot instance
bot = None

@app.on_event("startup")
async def startup_event():
    """Initialize bot on application startup"""
    global bot
    try:
        # Create template
        create_template()
        
        # Initialize bot
        bot = Chatbot()
        
        # Load knowledge base from files
        documents = load_knowledge_files()
        if documents:
            bot.add_knowledge(documents)
            logger.info(f"Loaded {len(documents)} documents into knowledge base")
        else:
            logger.warning("No knowledge files found in knowledge directory")
        
        logger.info("Bot successfully initialized")
    except Exception as e:
        logger.error(f"Error initializing bot: {str(e)}")
        raise

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root route, returns HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(message: Message):
    """Handle chat messages"""
    global bot
    try:
        if bot is None:
            raise HTTPException(status_code=500, detail="Bot not initialized")
        
        response = await bot.process_message(message.text)
        return response
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="info"
    )
