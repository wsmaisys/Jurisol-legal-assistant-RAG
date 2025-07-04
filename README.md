

# Jurisol: AI-Powered Indian Legal Assistant (RAG)

> **AI-powered legal research assistant for Indian law, using Retrieval-Augmented Generation (RAG) and Qdrant vector search.**

**Docker Hub:** [wasimansariiitm/jurisol-legal-assistant](https://hub.docker.com/r/wasimansariiitm/jurisol-legal-assistant)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/github/issues/wsmaisys/Jurisol-legal-assistant-RAG)

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

**Jurisol** is an intelligent, AI-powered legal research assistant for Indian law. It leverages Retrieval-Augmented Generation (RAG) and a Qdrant vector database to deliver precise, context-aware answers to your legal queries by searching and synthesizing information from a curated database of Indian legal documents.

---

## 🚀 Key Features

- **Instant Legal Insights:** Accurate, referenced answers to complex legal questions.
- **AI-Powered Search:** Combines natural language processing and vector search for deep, relevant results.
- **Indian Law Focus:** Specially tailored for Indian statutes, case law, and legal principles.
- **User-Friendly Interface:** Streamlit frontend for interactive chat; FastAPI backend for robust API.
- **Transparent Citations:** Every answer is backed by references to actual legal documents.

---

## � How Jurisol Works

1. **User Query:** Ask legal questions in natural language.
2. **Semantic Search:** Qdrant vector search retrieves the most relevant legal documents from the Indian law database.
3. **RAG Pipeline:** The AI model synthesizes retrieved information, generating a clear, context-aware answer with references.
4. **Response:** The user receives a concise, well-cited answer, ready for research or decision-making.

---

## 🧑‍� Tech Stack

- **Python 3.12+**
- **FastAPI** (backend API)
- **Streamlit** (frontend UI)
- **Qdrant** (vector database for semantic search)
- **MistralAI** (LLM and embeddings)
- **LangChain** (LLM orchestration, vector search, summarization)
- **TavilySearch** (online search tool for Indian government sites)
- **PyPDF2, BeautifulSoup4** (document parsing)
- **Docker** (containerization)

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
- Qdrant instance (local or managed)

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
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=your_qdrant_api_key
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

## 🚀 Production & Deployment Tips

- Use Docker for consistent deployment.
- Pass secrets and API keys via environment variables or Docker secrets.
- For scalability, run FastAPI and Streamlit in separate containers behind a reverse proxy (Nginx, Traefik).
- Use a managed Qdrant instance or run Qdrant in a separate container with persistent storage.
- Set up monitoring, logging, and health checks for robust production operation.

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
- Qdrant (vector database)
- Tavily (online search)
- Anthropic, OpenAI and GitHub (Brilliant AI tools).
- All contributors and supporters

---
