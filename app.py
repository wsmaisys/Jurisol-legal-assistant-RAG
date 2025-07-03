# Refactored app.py for Jurisol - Legal AI Assistant (stateless with compact history)

import os
import json
import asyncio
import time
import logging
from typing import Annotated, List, Dict, Any, Optional, TypedDict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from tools.vector_search_tool import search_indian_law_documents
from tools.online_search_tool import OnlineSearchTool
from tools.summarization_tool import SummarizationTool

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO)

app_state = {"llm": None, "graph": None, "executor": None, "tools": {}}

# --- System Prompt ---
SYSTEM_PROMPT = SystemMessage(content="""
You are Jurisol, a sophisticated AI-powered legal assistant with deep expertise in Indian Law and legal research.

🧠 CORE CAPABILITIES:
1. Legal Research & Analysis
   - Access to Indian legal databases and government sources
   - Ability to analyze case law, statutes, and legal documents
   - Integration of multiple legal sources into cohesive insights

2. Query Processing
   - Natural language understanding of legal questions
   - Context-aware response generation
   - Identification of relevant legal principles and precedents

3. Source Integration & Synthesis
   When working with legal sources (whether from vector search or online):
   - Automatically evaluate source credibility and relevance
   - Extract key legal principles and holdings
   - Connect findings to the user's specific situation
   - Synthesize information into actionable insights

📚 RESPONSE METHODOLOGY:
For every query, follow this integrated approach:
1. Context Analysis
   - Identify the legal domain and key issues
   - Frame the question within relevant Indian legal framework
   
2. Source Evaluation
   - Assess credibility and relevance of available sources
   - Extract pertinent legal principles and precedents
   - Connect sources to establish legal narrative

3. Legal Application
   - Apply extracted principles to the specific query
   - Consider practical implications and limitations
   - Identify relevant statutory provisions or case law

4. Synthesis & Presentation
   - Present findings in clear, structured format
   - Support conclusions with specific legal references
   - Highlight practical implications and next steps

🚫 BOUNDARIES:
- Strictly Indian law context only
- No speculation on rulings or citations
- Focus on information and analysis, not direct advice

🎯 OUTPUT STYLE:
Maintain a professional, authoritative tone while ensuring:
- Clear structure and logical flow
- Proper citation of legal sources
- Balanced analysis of legal principles
- Practical context and implications
- Actionable insights for further research

Remember: You are not just providing information, but offering sophisticated legal analysis integrated with source materials. Each response should demonstrate your ability to synthesize complex legal information into clear, actionable insights.""")

# --- Models ---
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    timestamp: float

# --- LangGraph State ---
class State(TypedDict):
    messages: Annotated[List[Any], ...]

# --- Intent Detection ---
def detect_intent(message: str) -> str:
    lowered = message.lower()
    if "case" in lowered and "summarize" in lowered:
        return "summarize_case"
    elif "case" in lowered or "judgment" in lowered:
        return "search_case"
    elif "summarize" in lowered:
        return "summarize"
    return "general"

# --- LangGraph Node ---
def tool_agent_node(state):
    messages = state["messages"]
    last_user_msg = messages[-1].content if messages else ""
    intent = detect_intent(last_user_msg)
    vector_tool = app_state["tools"].get("vector")
    summarizer = app_state["tools"].get("summarizer")
    online_tool = app_state["tools"].get("online")
    response = ""
    
    try:
        if intent in ["summarize_case", "search_case"]:
            results = vector_tool(last_user_msg)
            if results and (isinstance(results[0], dict) or (isinstance(results[0], str) and len(results[0].strip()) > 50)):
                content = results[0] if isinstance(results[0], str) else results[0].get('content', '')
                if intent == "summarize_case":
                    summary = summarizer(content)
                    response = f"📚 Summary of Indian Case Law:\n\n{summary}"
                else:
                    response = f"🔍 Indian Case Found:\n\n{content}"
            else:
                # Fallback to online search if vector search returns no or invalid results
                logging.info("Vector search returned no valid results, falling back to online search")
                alt_results = online_tool(last_user_msg)
                
                # Process search results
                search_content = []
                
                if isinstance(alt_results, (list, dict)):
                    # Handle structured results
                    if isinstance(alt_results, list):
                        for result in alt_results:
                            if isinstance(result, dict):
                                # Handle dictionary results (URLs and content)
                                if not result.get('error'):
                                    if 'content' in result:
                                        search_content.append(result['content'])
                                    elif 'url' in result:
                                        search_content.append(f"Source: {result['url']}")
                            else:
                                # Handle string results
                                search_content.append(str(result))
                    else:  # single dictionary
                        if not alt_results.get('error'):
                            if 'content' in alt_results:
                                search_content.append(alt_results['content'])
                            elif 'url' in alt_results:
                                search_content.append(f"Source: {alt_results['url']}")
                    
                    if search_content:
                        # Prepare context for LLM analysis
                        analysis_prompt = (
                            f"Legal Query: {last_user_msg}\n\n"
                            f"Available Legal Information:\n\n{chr(10).join(search_content)}\n\n"
                            f"Please provide a comprehensive legal analysis using the above information. "
                            f"Follow the response methodology to analyze the sources, extract relevant legal principles, "
                            f"and connect them to the query. Maintain focus on Indian law context and practical implications."
                        )
                        # Generate integrated response
                        response = app_state["llm"].invoke([
                            SYSTEM_PROMPT,
                            HumanMessage(content=analysis_prompt)
                        ]).content
                    else:
                        response = "⚠️ No valid legal sources found. Please try rephrasing your query."
                elif isinstance(alt_results, str):
                    # Handle plain text results
                    response = f"🌐 Legal Search Result:\n\n{alt_results}"
                else:
                    response = "⚠️ Unexpected search result format. Please try rephrasing your query."
        elif intent == "summarize":
            # Check if it's a direct paragraph summarization request
            if last_user_msg.lower().startswith("summarize this paragraph:"):
                paragraph = last_user_msg.split(":", 1)[1].strip()
                summary = summarizer(paragraph)
            elif "summarize:" in last_user_msg.lower():
                paragraph = last_user_msg.split("summarize:", 1)[1].strip()
                summary = summarizer(paragraph)
            else:
                # If no explicit paragraph marker, summarize the entire message
                summary = summarizer(last_user_msg)
            response = f"📝 Summary:\n\n{summary}"
        else:
            llm_response = app_state["llm"].invoke([SYSTEM_PROMPT] + messages).content
            if "i am unable to perform online searches" in llm_response.lower() or "based on the data i've been trained on" in llm_response.lower():
                reminder_prompt = HumanMessage(content="Remember: You have access to tools like vector search and online search (gov.in, nic.in) to find Indian legal content. Please use them before responding.")
                second_try = app_state["llm"].invoke([SYSTEM_PROMPT, reminder_prompt] + messages).content
                if "i am unable to perform online searches" in second_try.lower() or "based on the data i've been trained on" in second_try.lower():
                    response = "⚠️ I could not find relevant content through Indian legal sources at this time. Please refine your query or try again later."
                else:
                    response = second_try
            else:
                response = llm_response
    except Exception as e:
        logging.exception("Tool execution error")
        response = "⚠️ Sorry, something went wrong while processing your request. Please try again later."

    return {"messages": messages + [AIMessage(content=response)]}

# --- LangGraph Setup ---
def build_graph():
    sg = StateGraph(State)
    sg.add_node("agent", tool_agent_node)
    sg.set_entry_point("agent")
    sg.set_finish_point("agent")
    return sg.compile(checkpointer=MemorySaver())

# --- Initialization ---
def initialize():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logging.warning("Missing MISTRAL_API_KEY. LLM features may not function.")
        return

    llm = ChatMistralAI(model="mistral-small-latest", temperature=0, api_key=api_key)
    app_state["tools"] = {
        "vector": search_indian_law_documents,
        "summarizer": SummarizationTool(llm),
        "online": OnlineSearchTool(llm)
    }
    app_state["llm"] = llm
    app_state["graph"] = build_graph()
    app_state["executor"] = ThreadPoolExecutor(max_workers=8)

# --- API Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield
    if app_state["executor"]:
        app_state["executor"].shutdown()

app = FastAPI(title="Jurisol", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- API Routes ---
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", timestamp=time.time())

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_msg = {"role": "user", "content": request.message}
        # Use only last few messages to control token usage
        chat_history = request.history[-4:] if request.history else []

        lc_messages = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
            for m in chat_history if "content" in m
        ] + [HumanMessage(content=request.message)]

        result = await asyncio.get_event_loop().run_in_executor(
            app_state["executor"],
            lambda: app_state["graph"].invoke({"messages": lc_messages}, config={"configurable": {"thread_id": "stateless"}})
        )

        final_msg = result["messages"][-1].content

        return ChatResponse(response=final_msg, session_id="stateless", timestamp=time.time())
    except Exception as e:
        logging.exception("Chat processing error")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again later.")