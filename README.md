

# Jurisol: AI-Powered Indian Legal Assistant

Jurisol is an advanced AI-powered legal assistant tailored for Indian law. It leverages state-of-the-art language models, vector search, and custom tools to provide fast, accurate, and context-aware legal information and document analysis.

---

## 🚀 Key Features

- **Legal Document Search & Analysis:** Quickly search and analyze Indian legal documents, statutes, and case laws.
- **Access to Precedents:** Retrieve relevant Indian legal precedents and case law references.
- **Intelligent Query Understanding:** Natural language interface for complex legal queries.
- **Session-Based Conversations:** Maintains context and history for each user session.
- **Asynchronous & Robust Backend:** FastAPI backend with async processing and error recovery.
- **Clean, Modern UI:** Streamlit-based frontend for an intuitive chat experience.
- **Custom Tools:** Online search, summarization, and vector-based semantic search.

---

## 🗂️ Project Structure

```
LangGraph-Tutorial/
├── app.py                  # FastAPI backend server (main API)
├── frontend.py             # Streamlit frontend (chat interface)
├── requirements.txt        # Python dependencies
├── tools/                  # Custom tool implementations
│   ├── __init__.py
│   ├── online_search_tool.py      # Online legal document search
│   ├── summarization_tool.py      # Document summarization
│   └── vector_search_tool.py      # Vector database search
└── indian_law_vector_store/       # Vector database storage (ChromaDB)
    └── ...                        # Vector store files
```

---

## ⚙️ Technical Overview

### Backend (`app.py`)
- Built with **FastAPI** for high performance and async request handling
- Orchestrates workflows using **LangGraph**
- Integrates custom tools for search, summarization, and vector retrieval
- Manages user sessions and conversation state
- Provides robust error handling and health checks

### Frontend (`frontend.py`)
- Built with **Streamlit** for a modern, responsive chat UI
- Handles session state, error feedback, and user interaction
- Connects to backend via REST API

### Tools (`tools/`)
- **Online Search Tool:** Searches legal documents online (Tavily API)
- **Vector Search Tool:** Semantic search over local vector DB (ChromaDB)
- **Summarization Tool:** Summarizes legal documents and URLs

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- `pip` package manager
- (Recommended) Virtual environment

### Installation Steps
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd LangGraph-Tutorial
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```env
   MISTRAL_API_KEY=your_mistral_api_key
   ```

---

## ▶️ Running the Application

1. **Start the backend server:**
   ```bash
   python app.py
   ```
2. **Start the frontend in a new terminal:**
   ```bash
   streamlit run frontend.py
   ```
3. **Open your browser:**
   Visit [http://localhost:8501](http://localhost:8501)

---

## 💡 Usage Guide

1. Enter your legal query in the chat input (e.g., "What is the punishment for theft under IPC?")
2. Wait for the AI to process and respond with relevant legal information, statutes, or case law
3. Review the response and follow up with further questions as needed
4. Clear chat history or start a new session anytime

---

## ⚡ Performance & Optimization
- Connection pooling for efficient HTTP requests
- Fast vector search for legal documents
- Memory-optimized session and conversation management
- Robust error handling and automatic retries

## 🔒 Security & Reliability
- Secure session and state management
- Input validation and sanitization
- Rate limiting and error containment
- Health checks and logging

## 📝 Contributing
Contributions are welcome! To contribute:
1. Fork this repository
2. Create a new feature branch
3. Commit and push your changes
4. Open a Pull Request

---

## 📄 License
[Add appropriate license information here]

## 📬 Contact
[Add your contact information here]

## 🙏 Acknowledgments
- LangGraph (workflow orchestration)
- Mistral AI (language model)
- Streamlit (frontend framework)
- FastAPI (backend server)
- ChromaDB (vector database)
- All contributors and supporters

---

Created by Waseem M Ansari
