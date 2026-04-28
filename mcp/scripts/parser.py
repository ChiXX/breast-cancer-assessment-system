import json
import re
from mcp.agents.schemas import RiskLevel
from mcp.scripts.schemas import EvaluateResponse

def parse_agent_response(text: str) -> EvaluateResponse:
    """
    Parses the JSON response from MedicalMaster.
    """
    try:
        # LLMs sometimes wrap JSON in code blocks
        json_str = text
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(json_str)
        
        if data.get("type") == "evaluation":
            eval_data = data.get("data", {})
            advice = eval_data.get("advice", "")
            display_text = data.get("display_text", "")
            
            # If display_text is just a repeat of advice, or empty, handle it
            if not display_text or display_text == advice:
                display_text = "根据您的描述，我们为您整理了以下评估结果：" if not display_text else display_text

            return EvaluateResponse(
                risk_level=eval_data.get("risk_level", "未知"),
                action_required=eval_data.get("action_required"),
                ctcae_grade=eval_data.get("ctcae_grade"),
                advice=advice,
                contact_team=eval_data.get("contact_team", False),
                evidence=eval_data.get("evidence", ""),
                rule_id=eval_data.get("rule_id", ""),
                display_text=display_text
            )
        elif data.get("type") == "question":
            content = data.get("content", "")
            display_text = data.get("display_text", "")
            return EvaluateResponse(
                risk_level=RiskLevel.UNKNOWN,
                advice=content,
                contact_team=False,
                evidence="",
                rule_id="",
                display_text=display_text if display_text != content else ""
            )
        else:
            # Fallback or RAG direct output
            advice = data.get("advice", text)
            display_text = data.get("display_text", "")
            return EvaluateResponse(
                risk_level=data.get("risk_level", RiskLevel.UNKNOWN),
                advice=advice,
                contact_team=data.get("contact_team", False),
                evidence=data.get("evidence", ""),
                rule_id=data.get("rule_id", ""),
                display_text=display_text if display_text != advice else ""
            )
            
    except Exception as e:
        print(f"DEBUG: JSON parse failed, falling back to legacy regex. Error: {e}")
        # Legacy regex parsing as fallback
        risk_level = "未知"
        advice = text
        contact_team = False
        evidence = ""
        rule_id = ""

        risk_match = re.search(r"风险等级\s*\**\s*[：:]\s*(.*)", text)
        advice_match = re.search(r"下一步建议\s*\**\s*[：:]\s*(.*)", text)
        contact_match = re.search(r"是否建议联系团队\s*\**\s*[：:]\s*(.*)", text)
        evidence_match = re.search(r"(?:简单依据说明|参考依据和说明)\s*\**\s*[：:]\s*(.*)", text)
        rule_id_match = re.search(r"参考依据ID\s*\**\s*[：:]\s*([A-Za-z0-9_-]+)", text)

        if risk_match:
            risk_raw = risk_match.group(1).split('\n')[0].strip()
            risk_level = RiskLevel.HIGH if "高" in risk_raw else RiskLevel.MEDIUM if "中" in risk_raw else RiskLevel.LOW if "低" in risk_raw else risk_raw

        if advice_match:
            advice_text = advice_match.group(1)
            next_header = re.search(r"\n\s*[-*]\s+\*\*|是否建议联系团队|简单依据说明|参考依据ID|参考依据和说明", advice_text)
            advice = advice_text[:next_header.start()].strip() if next_header else advice_text.strip()
        
        if contact_match:
            contact_val = contact_match.group(1).split('\n')[0].strip().lower()
            contact_team = any(word in contact_val for word in ["是", "yes", "true", "建议"])
        
        if evidence_match:
            evidence_text = evidence_match.group(1)
            next_header = re.search(r"\n\s*[-*]\s+\*\*|参考依据ID", evidence_text)
            evidence = evidence_text[:next_header.start()].strip() if next_header else evidence_text.strip()
                
        if rule_id_match:
            rule_id = rule_id_match.group(1).strip()

        return EvaluateResponse(
            risk_level=risk_level,
            advice=advice,
            contact_team=contact_team,
            evidence=evidence,
            rule_id=rule_id,
            display_text=text
        )
