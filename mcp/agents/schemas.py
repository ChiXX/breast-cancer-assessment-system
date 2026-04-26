from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "未知"

class ActionRequired(str, Enum):
    IMMEDIATE = "立即线下就医"
    WITHIN_24H = "24小时内联系团队"
    CONTACT_TEAM = "联系团队"
    CLOSE_OBSERVATION = "密切观察"
    CONTINUE_OBSERVATION = "继续观察与记录"

class CTCAEGrade(str, Enum):
    GRADE_1 = "Grade 1"
    GRADE_2 = "Grade 2"
    GRADE_3 = "Grade 3"
    GRADE_4 = "Grade 4"
    GRADE_5 = "Grade 5"
    OTHER = "Other"

class EvaluationData(BaseModel):
    risk_level: RiskLevel = Field(..., description="风险等级")
    action_required: ActionRequired = Field(..., description="行动建议")
    ctcae_grade: str = Field(..., description="CTCAE 级别")
    advice: str = Field(..., description="处置建议")
    contact_team: bool = Field(..., description="是否建议联系医疗团队")
    evidence: str = Field(..., description="依据说明")
    rule_id: str = Field(..., description="参考指南 ID")

class AgentResponse(BaseModel):
    type: str = Field(..., description="响应类型 (evaluation/question)")
    data: Optional[EvaluationData] = None
    display_text: str = Field("", description="展示文本")
    content: Optional[str] = None # For question type
    
    def to_json(self):
        return self.model_dump_json()
