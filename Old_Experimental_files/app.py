import streamlit as st
from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import time
import json

load_dotenv()

# Pydantic schema for structured legal response
class LegalSection(BaseModel):
    """Legal section with citation and relevance"""
    section_name: str = Field(description="Full name of the legal section (e.g., 'Section 420 IPC')")
    citation: str = Field(description="Exact legal citation or provision text")
    relevance: str = Field(description="Why this section applies to the case")

class LegalAnalysis(BaseModel):
    """Structured legal analysis response"""
    applicable_laws: List[LegalSection] = Field(description="List of relevant legal sections and provisions (max 3)")
    legal_procedure: List[str] = Field(description="Step-by-step legal procedure to follow (max 4 concise steps)")
    strategic_advice: List[str] = Field(description="Key strategic recommendations for the case (max 3 actionable points)")
    legal_loopholes: List[str] = Field(description="Specific legal loopholes or weaknesses with supporting legal basis from provided context (max 4 detailed points)")
    key_risks: List[str] = Field(description="Major legal risks or challenges to be aware of (max 3 critical risks)")

# Initialize parser
parser = PydanticOutputParser(pydantic_object=LegalAnalysis)

def format_legal_analysis(analysis: LegalAnalysis) -> str:
    """Format the structured legal analysis for display"""
    formatted = []
    
    # Applicable Laws
    if analysis.applicable_laws:
        formatted.append("<div class='chat-message ai-message'>")
        formatted.append("<h5>⚖️ Applicable Legal Sections</h5>")
        for law in analysis.applicable_laws:
            formatted.append(f"<b>{law.section_name}</b><br>" \
                              f"<span style='margin-left:1em;'>• <i>Citation:</i> {law.citation}</span><br>" \
                              f"<span style='margin-left:1em;'>• <i>Relevance:</i> {law.relevance}</span><br><br>")
    
    # Legal Procedure
    if analysis.legal_procedure:
        formatted.append("<h5>📋 Legal Procedure</h5>")
        formatted.append("<ul style='margin-left:1em;'>")
        for procedure in analysis.legal_procedure:
            formatted.append(f"<li>{procedure}</li>")
        formatted.append("</ul>")
    
    # Strategic Advice
    if analysis.strategic_advice:
        formatted.append("<h5>🎯 Strategic Recommendations</h5>")
        formatted.append("<ul style='margin-left:1em;'>")
        for advice in analysis.strategic_advice:
            formatted.append(f"<li>{advice}</li>")
        formatted.append("</ul>")
    
    # Legal Loopholes
    if analysis.legal_loopholes:
        formatted.append("<h5>🔍 Legal Loopholes & Opportunities</h5>")
        formatted.append("<ul style='margin-left:1em;'>")
        for loophole in analysis.legal_loopholes:
            formatted.append(f"<li>{loophole}</li>")
        formatted.append("</ul>")
    
    # Key Risks
    if analysis.key_risks:
        formatted.append("<h5>⚠️ Key Legal Risks</h5>")
        formatted.append("<ul style='margin-left:1em;'>")
        for risk in analysis.key_risks:
            formatted.append(f"<li>{risk}</li>")
        formatted.append("</ul>")
    formatted.append('</div>')
    
    return "\n".join(formatted)

# Page configuration
st.set_page_config(
    page_title="Jurisol - AI Legal Assistant", 
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme professional styling
st.markdown("""
<style>
    /* Dark theme for Streamlit */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
        color: #ffffff;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    .chat-message {
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        border-left: 4px solid;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .user-message {
        background-color: #1e2329;
        border-left-color: #4a9eff;
        color: #e6e6e6;
        border: 1px solid #2d3748;
    }
    
    .ai-message {
        background-color: #162447;
        border-left-color: #00d4aa;
        color: #ffffff;
        border: 1px solid #2a4a72;
    }
    
    .disclaimer-box {
        background-color: #2d1b0e;
        border: 2px solid #ff6b35;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 1rem 0;
        color: #ffcc80;
        box-shadow: 0 4px 15px rgba(255,107,53,0.1);
    }
    
    .role-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        text-align: center;
        margin: 1rem 0;
        border: 2px solid #2d3748;
        transition: all 0.3s ease;
        color: #ffffff;
    }
    
    .role-card:hover {
        border-color: #4a9eff;
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(74,158,255,0.2);
    }
    
    .role-card h3 {
        color: #4a9eff;
        margin-bottom: 1rem;
    }
    
    .role-card p {
        color: #b8c5d6;
        margin-bottom: 1rem;
    }
    
    .role-card ul {
        color: #e6e6e6;
    }
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #0f3460, #1a1a2e);
        color: #ffffff;
        border: 2px solid #4a9eff;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #4a9eff, #0f3460);
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(74,158,255,0.3);
    }
    
    /* Sidebar dark theme */
    .css-1d391kg {
        background-color: #0e1117;
    }
    
    /* Text areas and inputs dark theme */
    .stTextArea textarea {
        background-color: #1e2329;
        color: #ffffff;
        border: 2px solid #2d3748;
        border-radius: 8px;
    }
    
    .stTextArea textarea:focus {
        border-color: #4a9eff;
        box-shadow: 0 0 10px rgba(74,158,255,0.3);
    }
    
    .stSelectbox > div > div {
        background-color: #1e2329;
        color: #ffffff;
        border: 2px solid #2d3748;
    }
    
    /* Progress bar styling */
    .stProgress .st-bo {
        background-color: #4a9eff;
    }
    
    /* Form styling */
    .stForm {
        background-color: #1a1a2e;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize vector store
@st.cache_resource
def load_vector_store():
    return Chroma(
        embedding_function=MistralAIEmbeddings(model="mistral-embed"),
        persist_directory='./indian_law_vector_store',
        collection_name='indian_law_docs'
    )

try:
    vector_store = load_vector_store()
except Exception as e:
    st.error(f"Error loading vector store: {str(e)}")
    st.stop()

# Header
st.markdown("""
<div class="main-header">
    <h1>⚖️ JURISOL</h1>
    <h3>AI-Powered Legal Assistant</h3>
    <p>Professional Legal Research & Strategy Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar with disclaimers and information
with st.sidebar:
    st.markdown("## ⚠️ LEGAL DISCLAIMER")
    
    st.markdown("""
    <div class="disclaimer-box">
    • This AI assistant provides information for research purposes only<br>
    • NOT a substitute for professional legal counsel<br>
    • Consult qualified attorneys for legal advice<br>
    • Information may contain errors or may be outdated<br>
    • User assumes all risks from using this service
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📋 Usage Guidelines")
    st.markdown("""
    <div style="color: #b8c5d6; line-height: 1.6;">
    - Be specific with your legal queries<br>
    - Mention relevant case details when applicable<br>
    - Ask for precedents if needed<br>
    - Request specific legal sections or acts<br>
    - Use for research and preliminary analysis only
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🔧 Features")
    st.markdown("""
    <div style="color: #b8c5d6; line-height: 1.6;">
    - <strong>Smart Legal Research</strong>: AI-powered document search<br>
    - <strong>Strategic Analysis</strong>: Identify legal loopholes and strategies<br>
    - <strong>Section Citations</strong>: Relevant legal provisions<br>
    - <strong>Role-Based Advice</strong>: Tailored for prosecution/defense
    </div>
    """, unsafe_allow_html=True)

# Session state initialization
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_acknowledged' not in st.session_state:
    st.session_state.user_acknowledged = False

# User acknowledgment
if not st.session_state.user_acknowledged:
    st.markdown("## 📋 Terms of Use & Acknowledgment")
    
    st.markdown("""
    <div class="disclaimer-box">
    <h4>⚠️ MANDATORY ACKNOWLEDGMENT</h4>
    By using Jurisol, you acknowledge and agree that:<br><br>
    
    1. <strong>No Attorney-Client Relationship</strong>: This service does not create any attorney-client relationship<br>
    2. <strong>For Research Only</strong>: Information provided is for research and educational purposes only<br>
    3. <strong>Seek Professional Advice</strong>: You will consult qualified legal professionals for actual legal matters<br>
    4. <strong>Accuracy Not Guaranteed</strong>: AI responses may contain errors and should be independently verified<br>
    5. <strong>Confidentiality Warning</strong>: Do not share sensitive case details or confidential information<br>
    6. <strong>Compliance Responsibility</strong>: You are responsible for ensuring compliance with applicable laws
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("I Acknowledge and Agree to Continue", key="acknowledge"):
            st.session_state.user_acknowledged = True
            st.rerun()
    
    st.stop()

# Role selection
if st.session_state.role is None:
    st.markdown("## 🎯 Select Your Legal Position")
    st.markdown("Choose your role to receive tailored legal strategies and advice:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="role-card">
            <h3>👨‍💼 Prosecution/Plaintiff</h3>
            <p>Representing the victim, complainant or prosecution</p>
            <ul style="text-align: left; padding-left: 2rem;">
                <li>Build strong cases</li>
                <li>Identify prosecution strategies</li>
                <li>Find supporting legal provisions</li>
                <li>Counter defense arguments</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Prosecution/Plaintiff", key='victim', use_container_width=True):
            st.session_state.role = 'prosecution'
            st.session_state.chat_history.append({
                'role': 'system', 
                'content': '🔴 **Role Selected**: You are now representing the **Prosecution/Plaintiff** side. I will provide strategic advice to build strong cases and identify legal advantages.'
            })
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="role-card">
            <h3>🛡️ Defense/Accused</h3>
            <p>Representing the accused, defendant or defense</p>
            <ul style="text-align: left; padding-left: 2rem;">
                <li>Identify defense strategies</li>
                <li>Find legal loopholes</li>
                <li>Challenge prosecution case</li>
                <li>Minimize legal exposure</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Defense/Accused", key='accused', use_container_width=True):
            st.session_state.role = 'defense'
            st.session_state.chat_history.append({
                'role': 'system', 
                'content': '🔵 **Role Selected**: You are now representing the **Defense/Accused** side. I will provide strategic advice to identify legal loopholes and defense strategies.'
            })
            st.rerun()
    
    st.stop()

# Chat interface
role_display = "Prosecution/Plaintiff" if st.session_state.role == 'prosecution' else "Defense/Accused"
role_color = "🔴" if st.session_state.role == 'prosecution' else "🔵"

st.markdown(f"## {role_color} Legal Strategy Console - {role_display}")

# Chat history display
chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong><br>{msg['content']}
            </div>
            """, unsafe_allow_html=True)
        elif msg['role'] == 'ai':
            # Render AI output in a styled div for consistency
            st.markdown(f"<div class='chat-message ai-message'><strong>🤖 Jurisol Legal Strategist:</strong><br>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.info(f"ℹ️ {msg['content']}")

# Query input
st.markdown("---")
with st.form(key='query_form', clear_on_submit=True):
    st.markdown("### 📝 Enter Your Legal Query")
    user_query = st.text_area(
        "Describe your legal question, case details, or situation:",
        placeholder="e.g., What are the key sections applicable for defamation in Indian law? How to defend against Section 420 IPC charges?",
        height=100
    )
    
    submitted = st.form_submit_button("🔍 Analyze Query", use_container_width=True)

if submitted and user_query.strip():
    st.session_state.chat_history.append({'role': 'user', 'content': user_query})

    with st.spinner('🔍 Analyzing legal documents and formulating strategy...'):
        progress_bar = st.progress(0)
        progress_bar.progress(25)
        time.sleep(0.5)

        try:
            results = vector_store.similarity_search(user_query, k=10)
            context = "\n\n".join([doc.page_content for doc in results])
            progress_bar.progress(50)
            time.sleep(0.5)

            # Build chat history for context
            history = ""
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    history += f"User: {msg['content']}\n"
                elif msg['role'] == 'ai':
                    history += f"AI: {msg['content']}\n"

            # Prepare role-specific prompt
            if st.session_state.role == "prosecution":
                role_instruction = (
                    "You are a cunning legal strategist for PROSECUTION/PLAINTIFF. "
                    "Analyze the case with precision and provide structured legal guidance. "
                    "Focus on building a strong prosecution case, identifying applicable laws, "
                    "legal procedures to follow, strategic advantages, and potential loopholes "
                    "that favor the prosecution. Keep responses concise and actionable."
                )
            else:
                role_instruction = (
                    "You are a cunning legal strategist for DEFENSE/ACCUSED. "
                    "Analyze the case with precision and provide structured legal guidance. "
                    "Focus on defense strategies, identifying applicable laws, legal procedures "
                    "for defense, strategic countermeasures, and exploitable loopholes that "
                    "can benefit the accused. Keep responses concise and actionable."
                )

            progress_bar.progress(75)

            # Enhanced prompt template with chat history
            template = PromptTemplate(
                template=(
                    "{role_instruction}\n\n"
                    "LEGAL CONTEXT FROM INDIAN LAW DATABASE:\n"
                    "==================================================\n"
                    "{context}\n"
                    "==================================================\n\n"
                    "CHAT HISTORY (for context, if any):\n"
                    "{history}\n"
                    "USER QUERY: {query}\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. Provide EXACTLY one structured JSON response following the schema\n"
                    "2. For legal_loopholes: Each point MUST reference laws/sections from the provided context\n"
                    "3. For legal_loopholes: Explain HOW the loophole works with legal reasoning\n"
                    "4. Keep each point concise but complete - no bullet lists within individual points\n"
                    "5. Use proper legal terminology and cite exact provisions\n"
                    "6. Total response should be under 500 words\n\n"
                    "Focus on:\n"
                    "- Applicable legal sections with exact citations\n"
                    "- Legal procedures to follow step-by-step\n"
                    "- Strategic recommendations for your role\n"
                    "- Legal loopholes supported by the provided legal context\n"
                    "- Key risks to consider\n\n"
                    "{format_instructions}"
                ),
                input_variables=["role_instruction", "context", "query", "history"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )

            prompt = template.format(
                role_instruction=role_instruction,
                context=context,
                query=user_query,
                history=history
            )

            progress_bar.progress(90)

            # Get AI response with structured output
            model = ChatMistralAI(model="mistral-small-latest", temperature=0.1)
            result = model.invoke(prompt)

            progress_bar.progress(95)

            # Parse structured response
            try:
                parsed_response = parser.parse(result.content)
                formatted_response = format_legal_analysis(parsed_response)
            except Exception as parse_error:
                # Fallback to raw response if parsing fails
                formatted_response = f"**Analysis:** {result.content}"
                st.warning("⚠️ Response parsing failed, showing raw analysis.")

            progress_bar.progress(100)
            time.sleep(0.3)
            progress_bar.empty()

            st.session_state.chat_history.append({'role': 'ai', 'content': formatted_response})
            st.rerun()

        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            progress_bar.empty()

# Control buttons
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Change Role", use_container_width=True):
        st.session_state.role = None
        st.session_state.chat_history = []
        st.rerun()

with col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

with col3:
    if st.button("📤 Export Chat", use_container_width=True):
        chat_export = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in st.session_state.chat_history])
        st.download_button(
            label="Download Chat History",
            data=chat_export,
            file_name=f"jurisol_chat_{role_display.lower()}_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px; border: 1px solid #2d3748;">
    <h5 style="color: #4a9eff; margin-bottom: 1rem;">⚖️ JURISOL - AI Legal Assistant</h5>
    <p style="margin: 0.5rem 0; color: #b8c5d6;">
        © 2024 Jurisol AI Legal Research Platform | 
        <strong style="color: #ff6b35;">For Research Purposes Only</strong> | 
        <strong style="color: #ff6b35;">Not Legal Advice</strong> | 
        <strong style="color: #00d4aa;">Consult Licensed Attorneys</strong>
    </p>
    <small style="color: #8a8a8a; display: block; margin-top: 1rem;">
        Always verify AI-generated legal information with qualified legal professionals.
        This platform does not create attorney-client relationships.
    </small>
</div>
""", unsafe_allow_html=True)