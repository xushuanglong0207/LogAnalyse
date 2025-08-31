from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ...database import get_db
from ...models.log import ParseRule, ParseRuleType
# from ...models.user import User  # 暂时注释，使用简单认证
# from ...auth.jwt_auth import get_current_user  # 暂时注释
from ...services.dsl_parser import DSLRuleEngine
from pydantic import BaseModel


router = APIRouter()


# 简单的认证依赖（临时解决方案）
def get_current_user():
    return {"id": 1, "username": "admin"}


class ParseRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    pattern: str
    problem_type: Optional[str] = None
    problem_description: Optional[str] = None
    priority: int = 0


class ParseRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rule_type: str
    pattern: str
    problem_type: Optional[str]
    problem_description: Optional[str]
    is_active: bool
    priority: int
    created_at: str
    
    class Config:
        from_attributes = True


class DSLTestRequest(BaseModel):
    rule_expression: str
    test_text: str


class DSLTestResponse(BaseModel):
    matched: bool
    error: Optional[str] = None
    rule: str
    test_text: str


@router.post("/test-dsl-rule", response_model=DSLTestResponse)
async def test_dsl_rule(
    test_data: DSLTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """测试DSL规则"""
    result = DSLRuleEngine.test_rule(test_data.rule_expression, test_data.test_text)
    return DSLTestResponse(**result)


@router.post("/rules", response_model=ParseRuleResponse)
async def create_rule(
    rule_data: ParseRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建解析规则"""
    
    # 验证规则类型
    try:
        rule_type = ParseRuleType(rule_data.rule_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的规则类型: {rule_data.rule_type}"
        )
    
    # 如果是DSL规则，先验证语法
    if rule_type == ParseRuleType.DSL:
        compiled_rule = DSLRuleEngine.compile_rule(rule_data.pattern)
        if not compiled_rule["compiled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DSL规则语法错误: {compiled_rule['error']}"
            )
    
    # 创建规则
    db_rule = ParseRule(
        name=rule_data.name,
        description=rule_data.description,
        rule_type=rule_type,
        pattern=rule_data.pattern,
        problem_type=rule_data.problem_type,
        problem_description=rule_data.problem_description,
        priority=rule_data.priority,
        created_by=current_user["id"]
    )
    
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return db_rule


@router.get("/rules", response_model=List[ParseRuleResponse])
async def get_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取所有解析规则"""
    rules = db.query(ParseRule).order_by(ParseRule.priority.desc()).all()
    return rules


@router.get("/rules/{rule_id}", response_model=ParseRuleResponse)
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单个解析规则"""
    rule = db.query(ParseRule).filter(ParseRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    return rule


@router.put("/rules/{rule_id}", response_model=ParseRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: ParseRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新解析规则"""
    rule = db.query(ParseRule).filter(ParseRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    # 验证规则类型
    try:
        rule_type = ParseRuleType(rule_data.rule_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的规则类型: {rule_data.rule_type}"
        )
    
    # 如果是DSL规则，先验证语法
    if rule_type == ParseRuleType.DSL:
        compiled_rule = DSLRuleEngine.compile_rule(rule_data.pattern)
        if not compiled_rule["compiled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DSL规则语法错误: {compiled_rule['error']}"
            )
    
    # 更新规则
    rule.name = rule_data.name
    rule.description = rule_data.description
    rule.rule_type = rule_type
    rule.pattern = rule_data.pattern
    rule.problem_type = rule_data.problem_type
    rule.problem_description = rule_data.problem_description
    rule.priority = rule_data.priority
    
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除解析规则"""
    rule = db.query(ParseRule).filter(ParseRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    
    return {"message": "规则删除成功"}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """启用/禁用规则"""
    rule = db.query(ParseRule).filter(ParseRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    rule.is_active = not rule.is_active
    db.commit()
    
    return {"message": f"规则已{'启用' if rule.is_active else '禁用'}"}