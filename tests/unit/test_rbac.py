"""Tests for RBAC role-to-permission mapping."""

from app.core.rbac import get_role_permissions, has_permission
from app.domain.enums import Permission, StaffRole


def test_triage_nurse_permissions():
    """Triage nurse can review but not close or manage staff."""
    role = StaffRole.TRIAGE_NURSE
    assert has_permission(role, Permission.VIEW_REQUEST)
    assert has_permission(role, Permission.ACCEPT_RECOMMENDATION)
    assert has_permission(role, Permission.MODIFY_RECOMMENDATION)
    assert has_permission(role, Permission.ESCALATE_REQUEST)
    assert has_permission(role, Permission.VIEW_AUDIT_LOG)
    assert not has_permission(role, Permission.CLOSE_REQUEST)
    assert not has_permission(role, Permission.MANAGE_STAFF)


def test_administrator_has_all_permissions():
    """Administrator holds every defined permission except unassigned ones."""
    role = StaffRole.ADMINISTRATOR
    perms = get_role_permissions(role)
    assert Permission.CLOSE_REQUEST in perms
    assert Permission.MANAGE_STAFF in perms
    assert Permission.VIEW_AUDIT_LOG in perms


def test_supervisor_can_close_but_not_manage_staff():
    """Supervisor can close requests but cannot manage staff accounts."""
    role = StaffRole.SUPERVISOR
    assert has_permission(role, Permission.CLOSE_REQUEST)
    assert not has_permission(role, Permission.MANAGE_STAFF)


def test_nurse_permissions_subset_of_administrator():
    """Administrator permissions are a superset of nurse permissions."""
    nurse = get_role_permissions(StaffRole.TRIAGE_NURSE)
    admin = get_role_permissions(StaffRole.ADMINISTRATOR)
    assert nurse.issubset(admin)


def test_get_role_permissions_returns_set():
    """get_role_permissions returns a non-empty set for known roles."""
    perms = get_role_permissions(StaffRole.TRIAGE_NURSE)
    assert isinstance(perms, frozenset)
    assert len(perms) > 0
