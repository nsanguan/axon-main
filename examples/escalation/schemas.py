"""
agents/executive/schemas.py
============================
PydanticAI contracts สำหรับ Executive Agent
ทุก input/output มี strict schema — ถ้า LLM ตอบผิด PydanticAI retry อัตโนมัติ
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    PO_DELAY           = "po_delay"
    PRODUCTION_BROKEN  = "production_broken"
    MACHINE_BROKEN     = "machine_broken"
    DAMAGE_STOCK       = "damage_stock"
    SAFETY_INCIDENT    = "safety_incident"
    DATA_BREACH        = "data_breach"
    SUPPLIER_CRISIS    = "supplier_crisis"
    CUSTOMER_COMPLAINT = "customer_complaint"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"


class ActionType(str, Enum):
    HALT        = "halt"        # หยุดกระบวนการ
    NOTIFY      = "notify"      # แจ้งเตือน stakeholder
    APPROVE     = "approve"     # อนุมัติงบ/แผน
    DEFER       = "defer"       # เลื่อนออกไป
    ESCALATE    = "escalate"    # ส่งต่อ BOD
    INVESTIGATE = "investigate" # ตั้งทีมสอบสวน


class HumanDecision(str, Enum):
    APPROVE = "approve"
    REJECT  = "reject"
    PENDING = "pending"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────────────────

class CustomerImpact(BaseModel):
    """ผลกระทบต่อลูกค้า"""
    customer_count_at_risk: int   = Field(..., ge=0)
    revenue_at_risk_thb:    float = Field(..., ge=0)
    delivery_delay_days:    int   = Field(..., ge=0)
    key_accounts_affected:  list[str] = Field(default_factory=list)


class StrategicAction(BaseModel):
    """
    Action ที่ Executive แนะนำ
    reversible บอก human ว่า undo ได้ไหม — สำคัญมากก่อนอนุมัติ
    """
    action_type:      ActionType
    target:           str   = Field(..., description="ใคร/อะไรที่ถูก action เช่น production_line_A, customer_TH001")
    description:      str   = Field(..., min_length=10)
    estimated_impact: str   = Field(..., description="ผลที่คาดว่าจะเกิดหลัง execute action นี้")
    reversible:       bool  = Field(..., description="True = ย้อนกลับได้, False = ถาวร ต้องระวัง")
    urgency_hours:    int   = Field(..., ge=0, description="ต้องทำภายในกี่ชั่วโมง")
    responsible_dept: str   = Field(..., description="แผนกที่ต้องดำเนินการ")


class EscalationStep(BaseModel):
    """ประวัติการ escalate — audit trail"""
    level:     str
    agent:     str
    summary:   str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — Executive รับอะไร
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveInput(BaseModel):
    """
    สิ่งที่ Director ส่งขึ้นมาให้ Executive
    ข้อมูลทุกอย่างถูก summarize มาแล้ว — Executive ไม่ดู raw data
    """
    # ── Event core ────────────────────────────────────────────────────────────
    event_type:           EventType
    severity_score:       float  = Field(..., ge=0, description="คำนวณโดย Supervisor")
    event_timestamp:      datetime = Field(default_factory=datetime.utcnow)

    # ── Context จาก lower levels ──────────────────────────────────────────────
    director_summary:     str    = Field(..., min_length=20,
                                         description="สรุปจาก Director — ทำอะไรไปแล้ว ทำไมแก้ไม่ได้")
    escalation_history:   list[EscalationStep] = Field(default_factory=list)
    affected_departments: list[str] = Field(..., min_length=1)

    # ── Business impact ───────────────────────────────────────────────────────
    financial_exposure_thb: float           = Field(..., ge=0)
    customer_impact:        Optional[CustomerImpact] = None

    # ── Deadline ──────────────────────────────────────────────────────────────
    decision_deadline_utc:  datetime = Field(
        ..., description="ต้องตัดสินใจภายในเมื่อไหร่ — Executive ต้องรู้ urgency"
    )

    @field_validator("affected_departments")
    @classmethod
    def must_have_departments(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("ต้องมี affected_departments อย่างน้อย 1 แผนก")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT — Executive ต้องตอบอะไร
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveOutput(BaseModel):
    """
    Output ที่ Executive Agent ต้องคืนค่า — strict schema
    PydanticAI จะ retry ถ้า LLM ตอบไม่ตรง
    """
    # ── Assessment ────────────────────────────────────────────────────────────
    risk_level:  RiskLevel = Field(..., description="ระดับความเสี่ยงโดยรวม")
    rationale:   str       = Field(..., min_length=50,
                                    description="เหตุผลการตัดสินใจ — ต้องอธิบายได้ชัดเจน")

    # ── Actions ───────────────────────────────────────────────────────────────
    recommended_actions: list[StrategicAction] = Field(
        ..., min_length=1, description="ต้องมีอย่างน้อย 1 action"
    )

    # ── Approval ──────────────────────────────────────────────────────────────
    requires_human_approval: bool = Field(
        default=True,
        description="ระดับ Executive ต้อง True เสมอ — ห้ามเปลี่ยนเป็น False"
    )

    # ── External comms ────────────────────────────────────────────────────────
    notify_external:        bool = Field(..., description="ต้องแจ้ง customer/supplier ภายนอกไหม")
    external_notify_list:   list[str] = Field(
        default_factory=list,
        description="รายชื่อ stakeholder ภายนอกที่ต้องแจ้ง"
    )

    # ── Timeline ──────────────────────────────────────────────────────────────
    estimated_resolution_hours: int = Field(..., ge=1, le=720,
                                             description="คาดว่าจะแก้ได้ใน ? ชั่วโมง")

    # ── Escalate further ─────────────────────────────────────────────────────
    escalate_to_board: bool = Field(
        default=False,
        description="True = ต้องส่งต่อ BOD — เช่น recall สินค้า, legal crisis"
    )
    board_escalation_reason: str = Field(
        default="",
        description="ต้องกรอกถ้า escalate_to_board=True"
    )

    # ── Summary for humans ────────────────────────────────────────────────────
    executive_brief: str = Field(
        ..., min_length=30,
        description="สรุปสั้น 2-3 ประโยคสำหรับ human approver อ่านก่อนอนุมัติ"
    )

    @field_validator("board_escalation_reason")
    @classmethod
    def board_reason_required_if_escalating(cls, v: str, info) -> str:
        if info.data.get("escalate_to_board") and not v:
            raise ValueError("ต้องกรอก board_escalation_reason เมื่อ escalate_to_board=True")
        return v

    @field_validator("requires_human_approval")
    @classmethod
    def must_require_approval(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Executive level ต้อง requires_human_approval=True เสมอ")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Intent Router schemas (บทบาทที่ 2 ของ Executive Agent)
# ─────────────────────────────────────────────────────────────────────────────

class IntentClassification(BaseModel):
    """
    Output ของ Executive ในโหมด Intent Router
    รับ user message → classify → route ไป flow ที่ถูกต้อง
    """
    intent_id:   str  = Field(..., description="unique intent identifier เช่น stock_check_reorder")
    flow_name:   str  = Field(..., description="ชื่อ flow ที่ต้อง trigger เช่น stock_check_reorder_flow")
    confidence:  float = Field(..., ge=0.0, le=1.0, description="ความมั่นใจ 0-1")
    entities:    dict  = Field(default_factory=dict, description="entities ที่ extract จาก message")
    priority:    Literal["urgent", "normal", "low"] = "normal"
    fallback:    bool  = Field(
        default=False,
        description="True = ไม่รู้ intent — ใช้ default flow"
    )

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence ต้องอยู่ระหว่าง 0.0 ถึง 1.0")
        return round(v, 3)
