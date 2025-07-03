
# Jurisol-An AI Legal Assistant-RAG

> **AI-powered legal research assistant for Indian law, using Retrieval-Augmented Generation (RAG) and vector search.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/github/issues/wsmaisys/Jurisol-legal-assistant-RAG)

---

## 📑 Table of Contents
- [Project Description](#project-description)
- [Key Features](#-key-features)
- [How Jurisol Works](#-how-jurisol-works)
- [Technologies Used](#-technologies-used)
- [Setup & Installation](#-setup--installation)
- [Usage Guide](#-usage-guide)
- [What Makes Jurisol Different?](#-what-makes-jurisol-different)
- [Contribution](#-contribution)
- [License](#-license)
- [Contact](#-contact)
- [Acknowledgments](#-acknowledgments)

---


## Project Description

**Jurisol Legal Assistant RAG** is your intelligent, AI-powered legal research companion designed to revolutionize the way you access, understand, and utilize Indian law. Leveraging advanced Retrieval-Augmented Generation (RAG) techniques, Jurisol delivers precise, context-aware answers to your legal queries by searching and synthesizing information from a curated vector database of Indian legal documents.

🚀 **Key Features:**
- **Instant Legal Insights:** Get accurate, well-referenced answers to complex legal questions in seconds.
- **AI-Powered Search:** Combines the power of natural language processing and vector search for deep, relevant results.
- **Indian Law Focus:** Specially tailored for Indian statutes, case law, and legal principles.
- **User-Friendly Interface:** Simple, intuitive, and ready for both legal professionals and students.

🔍 **Why Jurisol?**
Jurisol empowers you to cut through legal jargon, save research time, and make informed decisions with confidence. Whether you’re a lawyer, law student, or just curious about Indian law, Jurisol is your go-to assistant for reliable legal information.

---


## 🛠️ How Jurisol Works

1. **Query Input:** Users ask legal questions in natural language.
2. **Semantic Search:** The system uses advanced vector search to retrieve the most relevant legal documents, statutes, and case law from its curated Indian law database.
3. **Retrieval-Augmented Generation (RAG):** Jurisol’s AI model synthesizes the retrieved information, generating a clear, context-aware answer with references.
4. **Response Delivery:** The user receives a concise, well-cited answer, ready for legal research or decision-making.

### 🔄 Workflow Overview

1. **User Interface** → 2. **Query Preprocessing** → 3. **Vector Store Search (ChromaDB)** → 4. **RAG Model (LLM)** → 5. **Answer Generation & Citation** → 6. **User Output**

---


## 🧑‍💻 Technologies Used
---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- pip
- (Recommended) Virtual environment

### Installation Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/wsmaisys/Jurisol-legal-assistant-RAG.git
   cd Jurisol-legal-assistant-RAG
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
   # Example
   OPENAI_API_KEY=your_openai_key
   ```

---

## ▶️ Usage Guide

1. Start the backend server:
   ```bash
   python app.py
   ```
2. (Optional) Start the frontend:
   ```bash
   streamlit run frontend.py
   ```
3. Open your browser and interact with the assistant.
4. Example query: `What is the punishment for theft under IPC?`

---

- **Python**: Core programming language for backend logic and orchestration.
- **ChromaDB**: High-performance vector database for semantic search and document retrieval.
- **Large Language Models (LLMs)**: For natural language understanding and answer generation (e.g., OpenAI GPT, Llama, or similar).
- **RAG (Retrieval-Augmented Generation)**: Combines search and generative AI for accurate, context-rich responses.
- **Streamlit/FastAPI (optional)**: For building interactive user interfaces (can be extended).

---


## ✨ What Makes Jurisol Different?
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

- **Author:** [wsmaisys on GitHub](https://github.com/wsmaisys)
- **Contact:** wsmaisys@gmail.com

---

## 📬 Contact

For any queries, suggestions, or support, feel free to reach out:

- **GitHub:** [wsmaisys](https://github.com/wsmaisys)
- **Email:** wsmaisys@gmail.com

---

## 🙏 Acknowledgments
- LangGraph (workflow orchestration)
- Mistral AI (language model)
- Streamlit (frontend framework)
- FastAPI (backend server)
- ChromaDB (vector database)
- All contributors and supporters

---

- **India-Centric Legal Focus:** Unlike generic AI legal tools, Jurisol is purpose-built for Indian law, statutes, and case law, ensuring unmatched relevance and accuracy.
- **Transparent Citations:** Every answer is backed by references to actual legal documents, making it trustworthy for professional use.
- **Cutting-Edge RAG Pipeline:** Integrates the latest in vector search and generative AI for deep, context-aware legal research.
- **Customizable & Extensible:** Open-source and modular, allowing easy adaptation for new legal domains or jurisdictions.
- **User Empowerment:** Designed for both legal professionals and students, making advanced legal research accessible to all.

---
