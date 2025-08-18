


<div align="center">
  <img src="Jurisol%20Flux.png" alt="Jurisol Flux"/>
</div>

# Jurisol: AI-Powered Indian Legal Assistant (RAG)

> **AI-powered legal research assistant for Indian law, using Retrieval-Augmented Generation (RAG) and Chroma vector search.**

**Docker Hub:** [wasimansariiitm/jurisol-legal-assistant](https://hub.docker.com/r/wasimansariiitm/jurisol-legal-assistant)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/github/issues/wsmaisys/Jurisol-legal-assistant-RAG)
[![Live Demo](https://img.shields.io/badge/demo-live-success?logo=render)](https://jurisol-legal-assistant-rag.onrender.com)

**🌐 Live Demo:** [Try Jurisol Now!](https://jurisol-legal-assistant-rag.onrender.com)

---

## 📑 Table of Contents
- [Project Description](#project-description)
- [Key Features](#key-features)
- [How Jurisol Works](#how-jurisol-works)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Usage Guide](#usage-guide)
- [Production & Deployment](#production--deployment)
- [Contribution](#contribution)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---

## Project Description

**Jurisol** is an intelligent, AI-powered legal research assistant for Indian law. It leverages Retrieval-Augmented Generation (RAG) and a Chroma vector database to deliver precise, context-aware answers to your legal queries by searching and synthesizing information from a curated database of Indian legal documents.

---

## 🚀 Key Features

- **Advanced Legal Research:** 
  - Accurate, context-aware answers with automatic query classification
  - Combines vector search of legal documents with real-time online research
  - Transparent citations and references to legal sources
  
- **Enhanced Conversation Management:**
  - Multi-threaded chat with persistent conversation history
  - Thread search and organization capabilities
  - Streaming responses for better user experience
  
- **Intelligent Query Processing:**
  - Automatic distinction between legal queries and casual conversation
  - Enhanced response generation with relevant legal context
  - Fallback mechanisms for robust error handling
  
- **Specialized Indian Law Focus:**
  - Curated database of Indian statutes and legal documents
  - Integration with government legal resources
  - Context-aware responses based on Indian legal framework
  
- **Modern Technical Architecture:**
  - LangGraph for sophisticated workflow orchestration
  - MistralAI's latest models for improved responses
  - Modular tool system for extensible capabilities

---

## � How Jurisol Works

1. **User Query:** Ask legal questions in natural language.
2. **Semantic Search:** Chroma vector search retrieves the most relevant legal documents from the Indian law database.
3. **RAG Pipeline:** The AI model synthesizes retrieved information, generating a clear, context-aware answer with references.
4. **Response:** The user receives a concise, well-cited answer, ready for research or decision-making.

---

## 🧑‍� Tech Stack

- **Python 3.12+**
- **FastAPI** (backend API)
- **Streamlit** (frontend UI with multi-threaded chat support)
- **Chroma** (vector database for semantic search)
- **LangGraph** (workflow orchestration and tool chaining)
- **MistralAI** (LLM model: mistral-small-latest)
- **LangChain** (LLM orchestration, vector search, summarization)
- **TavilySearch** (online search tool for Indian government sites)
- **Checkpointing** (InMemorySaver for state persistence)
- **Docker** (containerization)

Core Features:
- Multi-threaded conversations with persistent history
- Intelligent query classification (legal vs casual)
- Context-aware response generation using vector and online search
- Enhanced error handling and response validation
- Modular tool architecture for extensibility
- Streaming responses for better UX
- Advanced frontend with thread management and search

---

## 🐳 Docker Usage

You can quickly run Jurisol using the pre-built Docker image from Docker Hub:

```bash
docker pull wasimansariiitm/jurisol-legal-assistant
docker run --env-file .env -p 8501:8501 wasimansariiitm/jurisol-legal-assistant
```

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.12 or higher
- Docker (for containerized deployment)
- Chroma database (local SQLite or remote)

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/wsmaisys/Jurisol-legal-assistant-RAG.git
   cd Jurisol-legal-assistant-RAG
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```
   CHROMA_HOST=localhost
   CHROMA_PORT=8000
   MISTRAL_API_KEY=your_mistral_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

4. **(Optional) Run with Docker:**
   ```bash
   docker build -t jurisol .
   docker run --env-file .env -p 8501:8501 jurisol
   ```

---

## ▶️ Usage Guide

1. **Start the backend and frontend (default Docker CMD):**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0
   ```
   Or run separately for development:
   ```bash
   uvicorn app:app --reload
   streamlit run frontend.py
   ```

2. **Open your browser:**  
   Visit [http://localhost:8501](http://localhost:8501) for the Streamlit UI.

3. **Example query:**  
   `What is the punishment for theft under IPC?`

---

## 🚀 Production & Deployment

### Live Demo
The application is deployed and available at:
[https://jurisol-legal-assistant-rag.onrender.com](https://jurisol-legal-assistant-rag.onrender.com)

### Deployment Tips
- Use Docker for consistent deployment
- Pass secrets and API keys via environment variables or Docker secrets
- For scalability, run FastAPI and Streamlit in separate containers behind a reverse proxy (Nginx, Traefik)
- Use a managed Chroma instance or run Chroma with SQLite for local development
- Set up monitoring, logging, and health checks for robust production operation

### Deployment Platforms
- Currently deployed on [Render](https://render.com)
- Can be deployed to any platform that supports Docker containers
- Suitable for deployment on AWS, GCP, Azure, or any cloud platform

---

## 🤝 Contribution

Contributions are welcome! To contribute:
1. Fork this repository
2. Create a new feature branch
3. Commit and push your changes
4. Open a Pull Request

---

## 📄 License

This project is licensed under the terms of the **MIT License**. See the LICENSE file for details.

---

## 📬 Contact

- **GitHub:** [wsmaisys](https://github.com/wsmaisys)
- **Email:** wsmaisys@gmail.com

---

## 🙏 Acknowledgments

- LangGraph (workflow orchestration)
- Mistral AI (language model)
- Streamlit (frontend framework)
- FastAPI (backend server)
- Chroma (vector database)
- Tavily (online search)
- Anthropic, OpenAI and GitHub (Brilliant AI tools).
- All contributors and supporters

---
