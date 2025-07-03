import os
import json
import asyncio
from typing import Annotated, TypedDict, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
import time

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_mistralai import ChatMistralAI
from langchain.tools import Tool
from dotenv import load_dotenv

from tools.online_search_tool import OnlineSearchTool
from tools.vector_search_tool import search_indian_law_documents
from tools.summarization_tool import SummarizationTool

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# --- Conversation Trimming Helper ---
def estimate_tokens(text: str) -> int:
    # Fast token estimation: ~4 chars per token for English
    return len(text) // 4

def trim_conversation(messages: list, max_tokens: int = 100000) -> list:
    """
    Trim conversation to fit within max_tokens (default: 100,000).
    Always keep system prompt and most recent messages.
    Uses fast token estimation.
    """
    if not messages:
        return messages
    # Always keep the first message if it's a system prompt
    system_prompt = None
    start_idx = 0
    if messages[0].get("role") == "system":
        system_prompt = messages[0]
        start_idx = 1
    # Count tokens backwards from the end
    total_tokens = 0
    selected = []
    for msg in reversed(messages[start_idx:]):
        content = msg["content"] if isinstance(msg, dict) else getattr(msg, "content", "")
        total_tokens += estimate_tokens(content)
        if total_tokens > max_tokens:
            break
        selected.append(msg)
    selected = list(reversed(selected))
    if system_prompt:
        return [system_prompt] + selected
    return selected

# Enhanced Logging Configuration
def configure_logging():
    """Configure comprehensive logging for the application"""
    import os
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure root logger
    logging.basicConfig(level=logging.INFO)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Create specific loggers
    loggers = {
        'api': logging.getLogger('api'),
        'tools': logging.getLogger('tools'),
        'session': logging.getLogger('session'),
        'graph': logging.getLogger('graph'),
        'system': logging.getLogger('system')
    }
    
    # Configure all loggers
    for logger in loggers.values():
        logger.handlers = []
        logger.propagate = True
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
    
    return loggers

# Initialize loggers
loggers = configure_logging()
api_logger = loggers['api']
tools_logger = loggers['tools']
session_logger = loggers['session']
graph_logger = loggers['graph']
system_logger = loggers['system']

system_logger.info("Starting Jurisol Legal Assistant API...")

# Load environment variables
load_dotenv()
system_logger.debug("Environment variables loaded")

# Global variables for app state
app_state = {
    "llm": None,
    "graph": None,
    "tools": None,
    "executor": None
}

# Request status tracking
request_status = {}
request_lock = RLock()

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Pydantic models for API
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: float

class HealthResponse(BaseModel):
    status: str
    timestamp: float

# Session management with LRU cache and optimized locking
from functools import lru_cache
from threading import RLock
from typing import Optional

sessions: Dict[str, List[Dict]] = {}
session_lock = RLock()  # Reentrant lock for better performance

@lru_cache(maxsize=1000)
def get_session_history(session_id: str) -> List[Dict]:
    """Get conversation history for a session with caching"""
    with session_lock:
        return sessions.get(session_id, []).copy()

def update_session_history(session_id: str, messages: List[Dict]) -> None:
    """Update conversation history and invalidate cache"""
    with session_lock:
        sessions[session_id] = messages
        get_session_history.cache_clear()

def clear_session(session_id: str) -> bool:
    """Clear conversation history for a session. Returns True if session existed."""
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]
            get_session_history.cache_clear()
            return True
        return False

# Enhanced Tool Logging
def log_tool_call(tool_name: str, input_data: str, output_data: Any):
    """
    Enhanced logging for tool calls with detailed input/output tracking
    and performance metrics.
    """
    exec_id = f"tool_{int(time.time()*1000)}"
    tools_logger.info(f"Tool Execution [{exec_id}] - {tool_name} started")
    tools_logger.debug(f"Tool Input [{exec_id}]:\n{input_data}")
    
    try:
        # Log output based on type
        if isinstance(output_data, list):
            tools_logger.info(f"Tool Output [{exec_id}] - List with {len(output_data)} items")
            for idx, item in enumerate(output_data, 1):
                if isinstance(item, dict):
                    # Log document details
                    if 'summary' in item:
                        tools_logger.info(f"Document {idx} [{exec_id}]:")
                        tools_logger.info(f"├─ URL: {item.get('url', 'N/A')}")
                        tools_logger.info(f"├─ Type: {item.get('content_type', 'N/A')}")
                        tools_logger.debug(f"├─ Summary: {item.get('summary', 'N/A')[:500]}...")
                        tools_logger.debug(f"└─ Context: {item.get('context', 'N/A')[:500]}...")
                    else:
                        tools_logger.info(f"Item {idx} [{exec_id}]: {str(item)[:200]}...")
                else:
                    tools_logger.info(f"Item {idx} [{exec_id}]: {str(item)[:200]}...")
        else:
            tools_logger.info(f"Tool Output [{exec_id}] - Single result")
            tools_logger.debug(f"Output content [{exec_id}]:\n{str(output_data)[:500]}...")
        
        tools_logger.info(f"Tool Execution [{exec_id}] - {tool_name} completed successfully")
    except Exception as e:
        tools_logger.error(f"Tool Execution [{exec_id}] - Error logging output: {str(e)}")
        tools_logger.exception("Detailed error trace:")

class LoggedTool(Tool):
    def __init__(self, tool: Tool):
        super().__init__(
            name=tool.name,
            description=tool.description,
            func=self._logged_func,
            return_direct=tool.return_direct
        )
        self._original_func = tool.func

    def _logged_func(self, input_str: str) -> Any:
        result = self._original_func(input_str)
        log_tool_call(self.name, input_str, result)
        return result

# Tool calling node
def tool_calling_llm(state: State):
    messages = state["messages"]
    logging.info(f"\nProcessing user query: {messages[-1].content if messages else 'No message'}")

    # Convert messages to dict format if needed
    messages_dict = []
    for msg in messages:
        if isinstance(msg, dict):
            messages_dict.append(msg)
        else:
            role = "user" if hasattr(msg, "role") and msg.role == "user" else "assistant"
            messages_dict.append({"role": role, "content": msg.content})

    # Add system prompt if missing
    if not messages_dict or messages_dict[0].get("role") != "system":
        system_prompt = {
            "role": "system",
            "content": """You are the world's most clever, logical, and resourceful legal assistant, with expertise surpassing the best lawyers. You have deep knowledge of Indian law, Supreme Court and High Court cases, and legal reasoning. Your job is to help any user—victim or accused—by providing the best possible legal information, options, and reasoning for their situation.

Guidelines:
- Treat every user with empathy, respect, and professionalism, regardless of whether they are a victim or accused.
- Use advanced legal logic and reasoning to analyze the user's case, facts, and needs. Always consider both sides of a legal issue.
- For victims: Explain their rights, remedies, and the best legal steps to protect themselves, with practical and actionable advice.
- For accused: Explain all possible legal defenses, procedural safeguards, and any loopholes or mitigating factors that may help their case, within the boundaries of the law.
- Always provide clear, step-by-step reasoning for your answers, citing relevant laws, precedents, or legal principles.
- If the user asks about loopholes or ways to avoid punishment, explain all legal options and procedural rights, but never encourage or assist with illegal actions or evidence tampering.
- Use simple, direct language, but do not oversimplify complex legal issues. Be honest about risks and uncertainties.
- Always clarify that you provide information, not legal advice, and recommend consulting a qualified lawyer for specific actions.
- Suggest legal aid resources, helplines, or official portals when appropriate.
- If a question is unclear or out of scope, ask for more details or clarify your limitations.

IMPORTANT: Be less verbose in your responses. Stick to the most important and key points only. Do not include unnecessary details or lengthy explanations. Do not alter the nature of your response or workflow in any other way."""
        }
        messages_dict = [system_prompt] + [msg if isinstance(msg, dict) else {"role": "user" if hasattr(msg, "content") else "assistant", "content": msg.content} for msg in messages]

    # --- TRIM conversation to fit context window ---
    trimmed_messages = trim_conversation(messages_dict)

    # Convert to Langchain messages for the LLM
    langchain_messages = []
    for msg in trimmed_messages:
        content = msg["content"] if isinstance(msg, dict) else getattr(msg, "content", "")
        role = msg["role"] if isinstance(msg, dict) else (msg.role if hasattr(msg, "role") else "user")
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))

    # Invoke LLM with tools
    result = app_state["llm"].invoke(langchain_messages)
    return {"messages": langchain_messages + [result]}

def initialize_app():
    """Initialize the LLM, tools, and graph with optimized settings"""
    try:
        # Initialize LLM with performance optimizations
        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_api_key or mistral_api_key.strip() == "":
            raise ValueError("MISTRAL_API_KEY environment variable is not set or is empty. Please add it to your .env file.")

        llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0.0,
            api_key=mistral_api_key.strip()
        )
        

        # Initialize tools
        online_search_tool = OnlineSearchTool(llm)
        summarization_tool = SummarizationTool(llm)
        tools = [
            LoggedTool(Tool(
                name="online_search_tool",
                description="Search and summarize Indian legal documents",
                func=online_search_tool
            )),
            LoggedTool(Tool(
                name="search_indian_law_documents",
                description="Search vector database of Indian laws",
                func=search_indian_law_documents
            )),
            LoggedTool(Tool(
                name="summarization_tool",
                description="Summarize the content of a given URL (PDF or HTML) using a provided LLM. Useful for extracting key points, legal principles, and human context from legal documents.",
                func=summarization_tool
            ))
        ]

        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)
        app_state["llm"] = llm_with_tools
        app_state["tools"] = tools

        # Build graph
        builder = StateGraph(State)
        builder.add_node("tool_calling_llm", tool_calling_llm)
        builder.add_node("tools", ToolNode(tools))

        builder.add_edge(START, "tool_calling_llm")
        builder.add_conditional_edges(
            "tool_calling_llm",
            tools_condition
        )
        builder.add_edge("tools", "tool_calling_llm")
        builder.add_edge("tool_calling_llm", END)

        graph = builder.compile(checkpointer=MemorySaver())
        app_state["graph"] = graph
        
        # Optimize thread pool for better concurrency
        app_state["executor"] = ThreadPoolExecutor(
            max_workers=min(32, (os.cpu_count() or 1) * 4),
            thread_name_prefix="jurisol_worker"
        )

        # Pre-warm the thread pool
        def warmup(): pass
        futures = [app_state["executor"].submit(warmup) for _ in range(4)]
        for f in futures: f.result()

        logging.info("Application initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error initializing application: {str(e)}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logging.info("Starting up Jurisol Legal Assistant API...")
    success = initialize_app()
    if not success:
        logging.error("Failed to initialize application")
        raise RuntimeError("Application initialization failed")
    
    yield
    
    # Shutdown
    logging.info("Shutting down Jurisol Legal Assistant API...")
    if app_state["executor"]:
        app_state["executor"].shutdown(wait=True)

# Create FastAPI app
app = FastAPI(
    title="Jurisol - Legal Assistant API",
    description="AI-powered legal assistant for Indian law",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_chat_request_async(message: str, session_id: str) -> tuple[str, List[Dict]]:
    """Process chat request asynchronously for lower latency."""
    try:
        # Get conversation history and add user message
        conversation_history = get_session_history(session_id)
        conversation_history.append({"role": "user", "content": message})
        logging.info(f"Processing query for session {session_id}: {message}")

        # Configure and execute graph with timeout
        TIMEOUT_SECONDS = 120  # Increased timeout to match test script
        try:
            response = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    app_state["executor"],
                    lambda: app_state["graph"].invoke(
                        {"messages": conversation_history},
                        config={"configurable": {"thread_id": session_id}}
                    )
                ),
                timeout=TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            error_msg = f"Timeout: LLM/tool execution exceeded {TIMEOUT_SECONDS} seconds."
            logging.error(f"{error_msg} for session {session_id}")
            raise RuntimeError(error_msg)
        if "messages" not in response:
            raise ValueError("Invalid response format from the language model")
        last_message = response["messages"][-1]
        if not hasattr(last_message, 'content'):
            raise ValueError("Invalid message format in response")
        # Update conversation history
        updated_history = []
        for msg in response["messages"]:
            if isinstance(msg, dict):
                updated_history.append(msg)
            else:
                role = "system"
                if hasattr(msg, "role"):
                    role = msg.role
                elif isinstance(msg, HumanMessage):
                    role = "user"
                elif isinstance(msg, AIMessage):
                    role = "assistant"
                elif isinstance(msg, SystemMessage):
                    role = "system"
                updated_history.append({
                    "role": role,
                    "content": msg.content
                })
        # Update session
        update_session_history(session_id, updated_history)
        logging.info(f"Response generated for session {session_id}")
        return last_message.content, updated_history
    except Exception as e:
        logging.error(f"Error processing chat request: {str(e)}")
        # Set request status to failed if possible
        with request_lock:
            request_status[session_id] = {
                "status": "failed",
                "timestamp": time.time(),
                "error": str(e)
            }
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if app_state["graph"] is not None else "unhealthy",
        timestamp=time.time()
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Main chat endpoint with improved error handling and async processing"""
    if not app_state["graph"]:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    current_time = time.time()
    status_info = {
        "status": "processing",
        "timestamp": current_time,
        "response": None
    }
    
    try:
        with request_lock:
            request_status[request.session_id] = status_info

        async def process_and_update():
            try:
                response_content, _ = await process_chat_request_async(
                    request.message,
                    request.session_id
                )
                with request_lock:
                    request_status[request.session_id].update({
                        "status": "completed",
                        "timestamp": time.time(),
                        "response": response_content
                    })
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Chat processing error for session {request.session_id}: {error_msg}")
                with request_lock:
                    request_status[request.session_id].update({
                        "status": "failed",
                        "timestamp": time.time(),
                        "error": error_msg
                    })

        background_tasks.add_task(process_and_update)
        
        return ChatResponse(
            response="Request accepted for processing",
            session_id=request.session_id,
            timestamp=current_time
        )
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Chat endpoint error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {error_msg}"
        )

@app.get("/sessions/{session_id}/history")
async def get_session_history_endpoint(session_id: str):
    """Get conversation history for a session"""
    try:
        history = get_session_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        logging.error(f"Error getting session history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def clear_session_endpoint(session_id: str):
    """Clear conversation history for a session"""
    try:
        clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        logging.error(f"Error clearing session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{session_id}")
async def get_request_status(session_id: str):
    """Get the status of a chat request for a session"""
    try:
        with request_lock:
            if session_id not in request_status:
                return {
                    "status": "not_found",
                    "timestamp": time.time()
                }
            
            status_info = request_status[session_id]
            
            # Clean up completed or failed requests older than 5 minutes
            current_time = time.time()
            if status_info["status"] in ["completed", "failed"] and \
               current_time - status_info["timestamp"] > 300:
                del request_status[session_id]
            
            return status_info
    except Exception as e:
        logging.error(f"Error getting request status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def list_sessions():
    """List all active sessions with optimized performance"""
    try:
        with session_lock:
            current_time = time.time()
            session_list = []
            
            for sid, messages in sessions.items():
                if messages:  # Only process non-empty sessions
                    timestamps = [msg.get("timestamp", 0) for msg in messages]
                    last_activity = max(timestamps) if timestamps else 0
                    
                    # Include only active sessions (within last 24 hours)
                    if current_time - last_activity < 86400:  # 24 hours in seconds
                        session_list.append({
                            "session_id": sid,
                            "message_count": len(messages),
                            "last_activity": last_activity
                        })
            
            return {
                "sessions": sorted(
                    session_list,
                    key=lambda x: x["last_activity"],
                    reverse=True
                )
            }
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error listing sessions: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False for production
        log_level="info",
        workers=1  # Single worker to maintain state consistency
    )