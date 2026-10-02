"""Completion Checklist 测试(移植自 miniMaster test_checklist.py)。"""
from __future__ import annotations

from agentmuster.orchestrator.checklist import ChecklistItem, CompletionChecklist


def _checklist() -> CompletionChecklist:
    return CompletionChecklist(goal="目标", items=[ChecklistItem("C1", "项1"),
                                                  ChecklistItem("C2", "项2")])


def test_apply_verdict_and_complete():
    cl = _checklist()
    assert not cl.is_complete  # 尚未验收(全部 None)不算完成
    cl.apply_verdict([{"item_id": "C1", "satisfied": True, "evidence": "e1"},
                      {"item_id": "C2", "satisfied": True, "evidence": "e2"}])
    assert cl.is_complete and cl.unmet() == []


def test_partial_verdict_and_unknown_item():
    cl = _checklist()
    cl.apply_verdict([{"item_id": "C1", "satisfied": True},
                      {"item_id": "C99", "satisfied": True}])  # 未知项被忽略
    assert [i.item_id for i in cl.unmet()] == ["C2"]


def test_false_verdict_records_evidence():
    cl = _checklist()
    cl.apply_verdict([{"item_id": "C1", "satisfied": False, "evidence": "缺少证据"}])
    assert cl.unmet()[0].evidence == "缺少证据"


def test_dict_roundtrip_and_render():
    cl = _checklist()
    cl.apply_verdict([{"item_id": "C1", "satisfied": True, "evidence": "证据"}])
    cl2 = CompletionChecklist.from_dict(cl.to_dict())
    assert cl2.goal == "目标" and cl2.items[0].satisfied is True
    text = cl2.render()
    assert "[x] C1" in text and "[?] C2" in text and "证据" in text


def test_empty_checklist_not_complete():
    assert not CompletionChecklist(goal="目标").is_complete
