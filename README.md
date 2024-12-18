![Chatbot](https://raw.githubusercontent.com/KazKozDev/ChatBot/main/images/banner.jpg)

# Website Chatbot
A simple knowledge-based chatbot for your website.

![Chatbot Demo](https://raw.githubusercontent.com/KazKozDev/ChatBot/main/images/demo.jpg)

## Installation
### 1. Download Files
Copy the `chatbot` folder to your website root:
```
chatbot/
├── chatbot.py
├── server.py
├── knowledge_loader.py
├── install_ollama.sh
├── knowledge/
│   └── company.txt
└── templates/
```

### 2. Install Ollama
```bash
# Make script executable
chmod +x install_ollama.sh
# Run installation
./install_ollama.sh
```

### 3. Install Python Packages
```bash
pip3 install fastapi uvicorn chromadb sentence-transformers pydantic jinja2
```

### 4. Configure Information
Edit the `knowledge/company.txt` file:
```text
# About Company
[Your company description]
# Working Hours
[Business hours]
# Services
[Your services]
# Contacts
[Contact information]
```

### 5. Launch the Bot
```bash
# Run in background
python3 server.py &
```

### 6. Add to Website
Insert before `</body>`:
```html
<script>
(function() {
    var script = document.createElement('script');
    script.src = '/chatbot/static/chat-widget.js';
    script.async = true;
    document.head.appendChild(script);
    
    script.onload = function() {
        ChatWidget.init({
            botName: 'Assistant',
            apiUrl: '/chatbot/chat'
        });
    };
})();
</script>
```

## Chat Configuration
Customize appearance:
```javascript
ChatWidget.init({
    botName: 'Your title',
    position: 'right',        // right or left
    width: '350px',          // window width
    height: '500px'          // window height
});
```

## Requirements
- Python 3.8+
- 2 GB free memory
- Python support on hosting

## Support
Email: support@example.com