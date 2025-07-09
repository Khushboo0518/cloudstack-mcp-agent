# ☁️ CloudStack MCP Agent

Create and manage virtual machines in Apache CloudStack using natural language through a Python-based MCP (Model Context Protocol) tool.

---

## 🔧 Features

- 🚀 Natural language VM creation
- 🌐 Connects to Apache CloudStack API
- 🧠 Uses MCP for intelligent command mapping
- 📜 Lists zones, templates, and service offerings
- 🖥️ Automatically deploys the closest matching VM

---

## 🧱 Prerequisites

- Docker installed
- Apache CloudStack Simulator running
- Python 3.8+
- API Key & Secret Key from ACS UI

---

## 🛠️ Setup Instructions

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/cloudstack-mcp-agent.git
   cd cloudstack-mcp-agent
Install dependencies


pip install -r requirements.txt
Run the server


python server.py
📦 File Structure




server.py          # Main logic for VM creation using MCP
README.md          # Project documentation
requirements.txt   # Python dependencies (if any)
🔑 API Configuration
Inside server.py, set your API key and secret key:


API_KEY = "your-api-key"
SECRET_KEY = "your-secret-key"
ENDPOINT = "http://your-cloudstack-endpoint/client/api"



✍️ Author
Khushboo – Developer & Cloud Enthusiast

