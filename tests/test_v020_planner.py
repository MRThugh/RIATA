"""
Unit tests for R.I.A.T.A v0.2.0 Command Planner & Multi-Step Engine.
Author: Ali Kamrani (MRThugh)

Verifies:
- Multi-step clause splitting in Persian and English
- CommandPlan and CommandStep structures and status transitions
- Step dependencies mapping
- Multi-step sequential execution through IntentRouter
- Strict failure isolation (skipping subsequent steps upon failure)
- Partial success and full success reporting
"""

import pytest

from app.core.config import get_config
from app.core.context.models import SessionContext
from app.engine.planner import CommandPlan, CommandStep, get_command_planner
from app.engine.router import IntentRouter, get_intent_router
from app.executor.result import STATUS_PARTIAL_SUCCESS, STATUS_SUCCESS


def test_command_planner_single_step():
    planner = get_command_planner()
    plan = planner.build_plan("Open Firefox")

    assert plan.is_single_step is True
    assert len(plan.steps) == 1
    assert plan.steps[0].intent.name == "OPEN_APPLICATION"
    assert plan.steps[0].dependencies == []


def test_command_planner_two_step_persian():
    planner = get_command_planner()
    # Persian conjunction " و "
    plan = planner.build_plan("Chrome رو باز کن و GitHub رو باز کن")

    assert plan.is_single_step is False
    assert len(plan.steps) == 2
    assert plan.steps[0].step_id == 1
    assert plan.steps[1].step_id == 2
    assert plan.steps[1].dependencies == [0]


def test_command_planner_two_step_english():
    planner = get_command_planner()
    # English conjunction " and "
    plan = planner.build_plan("open Chrome and open GitHub")

    assert plan.is_single_step is False
    assert len(plan.steps) == 2
    assert plan.steps[0].step_id == 1
    assert plan.steps[1].dependencies == [0]


def test_command_planner_three_step():
    planner = get_command_planner()
    plan = planner.build_plan("ترمینال رو باز کن و فایل منیجر رو باز کن و مشخصات سیستم")

    assert len(plan.steps) == 3
    assert plan.steps[1].dependencies == [0]
    assert plan.steps[2].dependencies == [1]


def test_router_executes_two_step_plan_in_dry_run():
    config = get_config()
    orig_dry_run = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()

        output = router.process("Chrome رو باز کن و Firefox رو باز کن", session_id="test-plan-dry")
        assert output.plan is not None
        assert len(output.plan.steps) == 2
        assert output.plan.status == "SUCCESS"
        assert output.result is not None
        assert output.result.success is True
        assert output.result.status == STATUS_SUCCESS
        assert "✓" in output.response_text
    finally:
        config.dry_run = orig_dry_run


def test_multi_step_failure_isolation_skips_remaining():
    config = get_config()
    orig_dry_run = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()

        # Step 1: Valid application (succeeds in dry-run)
        # Step 2: Totally nonexistent application that fails
        # Step 3: Terminal (should NOT be executed because step 2 failed!)
        command = "Chrome رو باز کن و برنامه nonexistent_fake_app_xyz_99 رو باز کن و ترمینال رو باز کن"
        output = router.process(command, session_id="test-plan-fail")

        assert output.plan is not None
        assert len(output.plan.steps) == 3
        # Step 1: SUCCESS
        assert output.plan.steps[0].status == "SUCCESS"
        # Step 2: FAILED
        assert output.plan.steps[1].status == "FAILED"
        # Step 3: SKIPPED (never executed!)
        assert output.plan.steps[2].status == "SKIPPED"

        assert output.plan.status == "PARTIAL_SUCCESS"
        assert output.result.status == STATUS_PARTIAL_SUCCESS
    finally:
        config.dry_run = orig_dry_run


def test_plan_serialization():
    planner = get_command_planner()
    plan = planner.build_plan("Open Firefox and open Downloads")
    d = plan.to_dict()

    assert "plan_id" in d
    assert "steps" in d
    assert len(d["steps"]) == 2
    assert d["steps"][0]["step_id"] == 1
    assert "dependencies" in d["steps"][1]
