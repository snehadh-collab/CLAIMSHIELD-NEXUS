import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.guardrails import apply_responsible_ai_guardrails
from app.services.policy_rag import get_relevant_policies
from app.services.brief_generator import generate_siu_brief
from app.services.data_service import data_service
from app.services.rules_engine import evaluate_claim_rules
from app.models.copilot import (
    CopilotContextResponse,
    BriefRequest,
    SIUBriefSchema
)
from app.config import settings

router = APIRouter(prefix="/api/v1/copilot", tags=["AI Copilot & RAG"])

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class CopilotChatRequest(BaseModel):
    case_id: str
    message: Optional[str] = None
    user_query: Optional[str] = None
    chat_history: List[ChatMessage] = Field(default_factory=list)
    case_context: Optional[str] = ""

class CopilotChatResponse(BaseModel):
    case_id: str
    reply: Optional[str] = None
    response: Optional[str] = None
    status: str = "PASSED_GUARDRAILS"
    confidence_score: float = 0.92
    disclaimer: Optional[str] = "CONFIDENTIAL SIU BRIEF — Generated using 100% synthetic healthcare claims data."
    sources: List[str] = Field(default_factory=list)

@router.get("/context/{case_id}", response_model=CopilotContextResponse)
def get_case_copilot_context(case_id: str):
    """Retrieves SIU case context and relevant policy RAG citations."""
    clean_id = case_id.replace("CASE-", "")
    claim = data_service.get_claim_by_id(clean_id)
    
    if not claim:
        summary = f"Case {case_id} investigation summary."
        flagged_rules = ["IMPOSSIBLE_GEOGRAPHY", "DUPLICATE_BILLING"]
    else:
        rule_flags = evaluate_claim_rules(claim, data_service.claims)
        summary = f"Claim {claim.claim_id} by Dr. {claim.provider_name or claim.provider_npi} for Member {claim.member_id}. CPT {claim.cpt_code}, Amount: ${claim.claim_amount:.2f}, Location: {claim.location}."
        flagged_rules = rule_flags.flag_reasons

    query = f"{summary} {' '.join(flagged_rules)}"
    policies = get_relevant_policies(query)

    return CopilotContextResponse(
        case_id=case_id,
        claim_summary=summary,
        flagged_rules=flagged_rules,
        relevant_policies=policies
    )

@router.post("/brief", response_model=SIUBriefSchema)
def generate_brief_endpoint(request: BriefRequest):
    """Generates structured Gemini AI / Fallback SIU investigation brief."""
    result = generate_siu_brief(
        case_id=request.case_id,
        claim_details=request.claim_details,
        flagged_rules=request.flagged_rules
    )
    return SIUBriefSchema.model_validate(result)

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat_endpoint(payload: CopilotChatRequest):
    """Multi-turn conversational SIU Copilot endpoint for human investigators."""
    query_text = payload.message or payload.user_query or "Summarize this case."
    
    # 1. Check Guardrails for blocked clinical queries
    dummy_brief = {"confidence_score": 0.9}
    guardrail_check = apply_responsible_ai_guardrails(dummy_brief, query_text)
    
    if guardrail_check.get("status") == "SAFETY_REFUSAL":
        return CopilotChatResponse(
            case_id=payload.case_id,
            reply=guardrail_check["message"],
            response=guardrail_check["message"],
            status="SAFETY_REFUSAL",
            confidence_score=0.0
        )

    # 2. Retrieve relevant policies using RAG
    matched_policies = get_relevant_policies(query_text)
    policy_text = "\n".join(matched_policies)

    # 3. Retrieve Gemini API Key
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if api_key and not api_key.startswith("YOUR_"):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
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
            {query_text}

            Provide a concise, professional, and actionable response for the investigator.
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            reply_text = response.text.strip()
            
            return CopilotChatResponse(
                case_id=payload.case_id,
                reply=reply_text,
                response=reply_text,
                status="PASSED_GUARDRAILS",
                confidence_score=0.92,
                disclaimer="DISCLAIMER: Generated using 100% synthetic claims data.",
                sources=matched_policies
            )
        except Exception as e:
            print(f"Copilot Gemini call warning: {str(e)}")

    # Fallback chat response
    reply_text = f"Based on policy citations for Case {payload.case_id}: 1. Context: {payload.case_context or 'Case under review.'} 2. Policy Grounding: {matched_policies[0] if matched_policies else 'Standard FWA guidelines apply.'}"
    return CopilotChatResponse(
        case_id=payload.case_id,
        reply=reply_text,
        response=reply_text,
        status="PASSED_GUARDRAILS",
        confidence_score=0.85,
        disclaimer="DISCLAIMER: Generated using 100% synthetic claims data.",
        sources=matched_policies
    )