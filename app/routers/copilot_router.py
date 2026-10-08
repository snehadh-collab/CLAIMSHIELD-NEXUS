import os
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from app.services.guardrails import apply_responsible_ai_guardrails
from app.services.policy_rag import get_relevant_policies

router = APIRouter(prefix="/api/v1/copilot", tags=["AI Copilot Chat"])

# Initialize Gemini Client
api_key = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
client = genai.Client(api_key=api_key)

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class CopilotChatRequest(BaseModel):
    case_id: str
    message: str
    chat_history: Optional[List[ChatMessage]] = []
    case_context: Optional[str] = ""

class CopilotChatResponse(BaseModel):
    case_id: str
    reply: str
    status: str
    confidence_score: float
    disclaimer: Optional[str] = None

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat_endpoint(payload: CopilotChatRequest):
    """Multi-turn conversational SIU Copilot endpoint for human investigators."""
    
    # 1. Check Guardrails for blocked clinical queries
    dummy_brief = {"confidence_score": 0.9}
    guardrail_check = apply_responsible_ai_guardrails(dummy_brief, payload.message)
    
    if guardrail_check.get("status") == "SAFETY_REFUSAL":
        return CopilotChatResponse(
            case_id=payload.case_id,
            reply=guardrail_check["message"],
            status="SAFETY_REFUSAL",
            confidence_score=0.0
        )

    # 2. Retrieve relevant policies using RAG
    matched_policies = get_relevant_policies(payload.message)
    policy_text = "\n".join(matched_policies)

    # 3. Construct Conversational Context Prompt
    history_formatted = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in payload.chat_history])

    system_prompt = f"""
    You are ClaimShield Copilot, an expert AI assistant helping healthcare SIU (Special Investigations Unit) investigators.
    Answer the investigator's question based on the case details, policy rules, and conversation history.

    CASE ID: {payload.case_id}
    CASE CONTEXT: {payload.case_context or 'Flagged for impossible travel and duplicate billing.'}

    RELEVANT POLICY RULES:
    {policy_text}

    PREVIOUS CHAT HISTORY:
    {history_formatted}

    USER QUESTION:
    {payload.message}

    Provide a concise, professional, and actionable response for the investigator.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
            ),
        )
        reply_text = response.text.strip()
        
        return CopilotChatResponse(
            case_id=payload.case_id,
            reply=reply_text,
            status="PASSED_GUARDRAILS",
            confidence_score=0.92,
            disclaimer="DISCLAIMER: Generated using 100% synthetic claims data."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copilot API error: {str(e)}")