import streamlit as st
from app import chatbot
from langchain_core.messages import HumanMessage, BaseMessage
import uuid
import time

# **************************************** Configuration *************************
st.set_page_config(
    page_title="Jurisol - AI Legal Assistant",
    page_icon="⚖️",
    layout="centered"
)

# **************************************** Utility Functions *************************

def generate_thread_id():
    """Generate a unique thread ID - removed caching to ensure new IDs"""
    return str(uuid.uuid4())

def reset_chat():
    """Reset chat session with new thread and save current thread"""
    # Save current thread to persistent storage if it has messages
    if (st.session_state.get('message_history') and 
        len(st.session_state['message_history']) > 0):
        save_thread_to_storage(st.session_state['thread_id'], st.session_state['message_history'])
    
    # Generate new thread ID
    new_thread_id = generate_thread_id()
    
    # Update session state with new thread
    st.session_state.update({
        'thread_id': new_thread_id,
        'message_history': [],
        'processing': False
    })
    
    # Add new thread to the list
    add_thread(new_thread_id)
    print(f"[DEBUG] New thread created: {new_thread_id}")

def save_thread_to_storage(thread_id, messages):
    """Save thread messages to persistent storage"""
    if 'thread_storage' not in st.session_state:
        st.session_state['thread_storage'] = {}
    
    # Only save if there are actual messages
    if messages and len(messages) > 0:
        st.session_state['thread_storage'][thread_id] = {
            'messages': messages.copy(),
            'created_at': time.time(),
            'last_updated': time.time()
        }
        print(f"[DEBUG] Saved thread {thread_id} with {len(messages)} messages")

def load_thread_from_storage(thread_id):
    """Load thread messages from persistent storage"""
    if 'thread_storage' not in st.session_state:
        st.session_state['thread_storage'] = {}
    
    if thread_id in st.session_state['thread_storage']:
        stored_data = st.session_state['thread_storage'][thread_id]
        print(f"[DEBUG] Loaded thread {thread_id} from storage with {len(stored_data['messages'])} messages")
        return stored_data['messages']
    
    # If not in storage, try loading from backend
    backend_messages = load_conversation(thread_id)
    if backend_messages:
        formatted_messages = format_messages_for_display(backend_messages)
        # Save to storage for faster access next time
        save_thread_to_storage(thread_id, formatted_messages)
        print(f"[DEBUG] Loaded thread {thread_id} from backend with {len(formatted_messages)} messages")
        return formatted_messages
    
    return []

def add_thread(thread_id):
    """Add thread to chat threads list"""
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    """Load conversation from backend - removed caching to ensure fresh data"""
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        return state.values.get('messages', []) if state and hasattr(state, 'values') else []
    except Exception as e:
        st.error(f"Error loading conversation: {str(e)}")
        return []

def get_thread_preview(thread_id, max_length=50):
    """Get a preview of the thread's first message for display"""
    try:
        # First try to get from storage
        messages = load_thread_from_storage(thread_id)
        
        if messages:
            # Get the first user message as preview
            for msg in messages:
                if msg['role'] == 'user':
                    preview = msg['content'][:max_length]
                    if len(msg['content']) > max_length:
                        preview += "..."
                    return preview
        
        return "New conversation"
    except Exception as e:
        print(f"[DEBUG] Error getting thread preview for {thread_id}: {e}")
        return "Conversation"

def delete_thread(thread_id):
    """Delete a thread from the session and storage"""
    if thread_id in st.session_state['chat_threads']:
        st.session_state['chat_threads'].remove(thread_id)
    
    # Remove from storage
    if 'thread_storage' in st.session_state and thread_id in st.session_state['thread_storage']:
        del st.session_state['thread_storage'][thread_id]
    
    print(f"[DEBUG] Deleted thread: {thread_id}")
    
    # If we're deleting the current thread, switch to a new one
    if thread_id == st.session_state['thread_id']:
        reset_chat()

def format_messages_for_display(messages):
    """Convert backend messages to display format efficiently"""
    display_messages = []
    
    for msg in messages:
        # Skip tool messages
        if hasattr(msg, 'tool_call_id'):
            continue
            
        # Determine role and extract content
        if isinstance(msg, HumanMessage):
            role = 'user'
        else:
            role = 'assistant'
        
        content = getattr(msg, 'content', '')
        if content and content.strip():
            display_messages.append({'role': role, 'content': content.strip()})
    
    return display_messages

def get_assistant_response(user_input, config):
    """Get response from assistant with proper error handling"""
    try:
        response = chatbot.invoke(
            {'messages': [HumanMessage(content=user_input)]},
            config=config
        )
        
        # Extract assistant message more efficiently
        if response and 'messages' in response:
            # Get the last assistant message
            for msg in reversed(response['messages']):
                if (not hasattr(msg, 'tool_call_id') and 
                    not isinstance(msg, HumanMessage) and
                    hasattr(msg, 'content') and 
                    isinstance(msg.content, str) and 
                    msg.content.strip()):
                    return msg.content.strip()
        
        return "I apologize, but I couldn't generate a proper response. Please try again."
        
    except Exception as e:
        st.error(f"Error getting response: {str(e)}")
        return "I encountered an error while processing your request. Please try again."

# **************************************** Custom CSS *********************************
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 10px;
        border-radius: 10px;
        background-color: #f8f9fa;
        margin-bottom: 20px;
    }
    
    .processing-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #666;
        font-style: italic;
        font-size: 0.9em;
        padding: 10px;
        background-color: #e3f2fd;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
    }
    
    .typing-dots {
        display: inline-flex;
        gap: 4px;
    }
    
    .typing-dots span {
        height: 8px;
        width: 8px;
        background-color: #666;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    .error-message {
        color: #d32f2f;
        background-color: #ffebee;
        padding: 10px;
        border-radius: 8px;
        border-left: 4px solid #d32f2f;
    }
    
    .sidebar-thread {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 200px;
    }
    
    .thread-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px;
        margin: 2px 0;
        border-radius: 8px;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        transition: all 0.2s ease;
    }
    
    .thread-item:hover {
        background-color: #e9ecef;
        border-color: #dee2e6;
    }
    
    .thread-item.active {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    
    .thread-preview {
        flex: 1;
        font-size: 0.85em;
        color: #666;
        text-align: left;
        padding-right: 8px;
    }
    
    .thread-actions {
        display: flex;
        gap: 4px;
    }
    
    .delete-btn {
        background: none;
        border: none;
        color: #dc3545;
        font-size: 0.8em;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
        transition: background-color 0.2s;
    }
    
    .delete-btn:hover {
        background-color: #ffebee;
    }
    
    .search-box {
        width: 100%;
        padding: 8px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-size: 0.9em;
    }
    
    .threads-container {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 5px;
    }
    
    .thread-count {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# **************************************** Session Setup ******************************
def initialize_session():
    """Initialize session state variables"""
    defaults = {
        'message_history': [],
        'thread_id': generate_thread_id(),
        'chat_threads': [],
        'processing': False,
        'search_query': '',
        'show_all_threads': True,
        'thread_storage': {}  # For persistent thread storage
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Ensure current thread is in threads list
    add_thread(st.session_state['thread_id'])

initialize_session()

# **************************************** Sidebar UI *********************************
with st.sidebar:
    st.title('⚖️ Jurisol')
    st.caption('AI Legal Assistant')
    
    if st.button('🆕 New Chat', use_container_width=True):
        print(f"[DEBUG] New Chat button clicked. Current thread: {st.session_state['thread_id']}")
        print(f"[DEBUG] Current message history length: {len(st.session_state.get('message_history', []))}")
        
        reset_chat()
        st.rerun()
    
    st.divider()
    
    if st.session_state['chat_threads']:
        st.subheader('💬 All Conversations')
        
        # Search functionality
        search_query = st.text_input(
            "🔍 Search conversations...", 
            value=st.session_state.get('search_query', ''),
            placeholder="Enter keywords to search",
            key="thread_search"
        )
        st.session_state['search_query'] = search_query
        
        # Get all threads (no limitation)
        all_threads = st.session_state['chat_threads'][::-1]  # Most recent first
        
        # Filter threads based on search query
        if search_query:
            filtered_threads = []
            for thread_id in all_threads:
                thread_preview = get_thread_preview(thread_id, max_length=100)
                if search_query.lower() in thread_preview.lower():
                    filtered_threads.append(thread_id)
            display_threads = filtered_threads
        else:
            display_threads = all_threads
        
        # Show thread count
        total_threads = len(st.session_state['chat_threads'])
        showing_threads = len(display_threads)
        
        if search_query:
            st.markdown(f'<div class="thread-count">Showing {showing_threads} of {total_threads} conversations</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="thread-count">{total_threads} total conversations</div>', 
                       unsafe_allow_html=True)
        
        # Scrollable container for threads
        st.markdown('<div class="threads-container">', unsafe_allow_html=True)
        
        if display_threads:
            for i, thread_id in enumerate(display_threads):
                thread_preview = get_thread_preview(thread_id)
                is_active = thread_id == st.session_state['thread_id']
                
                # Create columns for thread item
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # Thread button with preview
                    button_label = f"Chat {total_threads - st.session_state['chat_threads'].index(thread_id)}"
                    if st.button(
                        button_label,
                        key=f"thread_btn_{thread_id}",
                        help=thread_preview,
                        use_container_width=True,
                        disabled=st.session_state['processing'] or is_active,
                        type="primary" if is_active else "secondary"
                    ):
                        if thread_id != st.session_state['thread_id']:
                            # Save current thread before switching
                            if (st.session_state.get('message_history') and 
                                len(st.session_state['message_history']) > 0):
                                save_thread_to_storage(st.session_state['thread_id'], 
                                                     st.session_state['message_history'])
                            
                            print(f"[DEBUG] Switching from thread {st.session_state['thread_id']} to {thread_id}")
                            
                            # Switch to the selected thread
                            st.session_state['thread_id'] = thread_id
                            
                            # Load the selected conversation
                            messages = load_thread_from_storage(thread_id)
                            st.session_state['message_history'] = messages
                            
                            print(f"[DEBUG] Loaded {len(messages)} messages for thread {thread_id}")
                            st.rerun()
                
                with col2:
                    # Delete button
                    if st.button(
                        "🗑️", 
                        key=f"delete_{thread_id}",
                        help="Delete conversation",
                        disabled=st.session_state['processing']
                    ):
                        delete_thread(thread_id)
                        st.rerun()
                
                # Show thread preview
                st.markdown(f'<div class="thread-preview">{thread_preview}</div>', 
                           unsafe_allow_html=True)
                
                if i < len(display_threads) - 1:  # Don't add divider after last item
                    st.markdown("---")
        
        else:
            if search_query:
                st.info("No conversations found matching your search.")
            else:
                st.info("No conversations yet. Start a new chat!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Bulk actions
        if len(st.session_state['chat_threads']) > 1:
            st.divider()
            st.subheader('🛠️ Manage Conversations')
            
            if st.button('🗑️ Clear All Conversations', 
                        use_container_width=True,
                        disabled=st.session_state['processing']):
                # Show confirmation dialog
                with st.popover("⚠️ Confirm Action"):
                    st.write("This will delete all conversations permanently.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('✅ Confirm', type="primary", use_container_width=True):
                            st.session_state['chat_threads'] = []
                            st.session_state['thread_storage'] = {}
                            reset_chat()
                            st.success("All conversations cleared!")
                            st.rerun()
                    with col2:
                        if st.button('❌ Cancel', use_container_width=True):
                            st.rerun()
    
    else:
        st.info("Start your first conversation!")
        
    # Show current thread info
    st.divider()
    st.caption(f"Current: {st.session_state['thread_id'][-8:]}")  # Show last 8 chars of thread ID

# **************************************** Main UI ************************************
# Centered title and caption using markdown and custom CSS
st.markdown("""
<div style="text-align: center;">
    <h1>Jurisol - AI Legal Assistant</h1>
    <p style="font-size:1.1em; color: #666;">Ask me anything about legal matters</p>
</div>
""", unsafe_allow_html=True)

# Display conversation history
if st.session_state['message_history']:
    for message in st.session_state['message_history']:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

# Handle user input
if user_input := st.chat_input('Ask your legal question...', disabled=st.session_state['processing']):
    # Prevent processing if already processing
    if st.session_state['processing']:
        st.warning("Please wait for the current response to complete.")
        st.stop()
    
    # Set processing state
    st.session_state['processing'] = True
    
    # Add user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    
    # Save current state before sending to backend
    save_thread_to_storage(st.session_state['thread_id'], st.session_state['message_history'])
    
    # Display user message
    with st.chat_message('user'):
        st.markdown(user_input)
    
    print(f"[DEBUG] User input: {user_input}")
    print(f"[DEBUG] Current thread ID: {st.session_state['thread_id']}")
    print(f"[DEBUG] Sending to backend with thread_id: {st.session_state['thread_id']}")
    
    # Display assistant response
    with st.chat_message('assistant'):
        # Show processing indicator
        with st.empty():
            st.markdown("""
            <div class="processing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                Jurisol is thinking...
            </div>
            """, unsafe_allow_html=True)
            
            # Get response from backend with correct thread_id
            config = {'configurable': {'thread_id': st.session_state['thread_id']}}
            
            start_time = time.time()
            response_content = get_assistant_response(user_input, config)
            response_time = time.time() - start_time
            
            print(f"[DEBUG] Backend response: {response_content[:100]}...")
            print(f"[DEBUG] Response time: {response_time:.2f}s")
            
            # Clear processing indicator and show response
            st.empty()
            st.markdown(response_content)
            
            # Optional: Show response time for debugging
            if st.session_state.get('show_debug_info', False):
                st.caption(f"Response time: {response_time:.2f}s")
    
    # Add assistant response to history
    st.session_state['message_history'].append({'role': 'assistant', 'content': response_content})
    
    # Save updated conversation
    save_thread_to_storage(st.session_state['thread_id'], st.session_state['message_history'])
    
    # Reset processing state
    st.session_state['processing'] = False
    
    # Force rerun to update UI
    st.rerun()

# **************************************** Footer *********************************
st.divider()
st.caption('💡 Tip: Be specific in your legal questions for more accurate responses.')

# Debug panel (optional - can be removed in production)
if st.sidebar.checkbox('Show Debug Info'):
    st.session_state['show_debug_info'] = True
    with st.sidebar.expander('Debug Information'):
        st.write(f"Thread ID: {st.session_state['thread_id']}")
        st.write(f"Messages in history: {len(st.session_state['message_history'])}")
        st.write(f"Processing: {st.session_state['processing']}")
else:
    st.session_state['show_debug_info'] = False