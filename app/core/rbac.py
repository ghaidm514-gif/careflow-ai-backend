"""Role-Based Access Control (RBAC) configuration."""

from app.domain.enums import Permission, StaffRole

ROLE_PERMISSIONS: dict[StaffRole, frozenset[Permission]] = {
    StaffRole.TRIAGE_NURSE: frozenset(
        {
            Permission.VIEW_REQUEST,
            Permission.ACCEPT_RECOMMENDATION,
            Permission.MODIFY_RECOMMENDATION,
            Permission.ESCALATE_REQUEST,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
    StaffRole.ADMINISTRATOR: frozenset(
        {
            Permission.VIEW_REQUEST,
            Permission.ACCEPT_RECOMMENDATION,
            Permission.MODIFY_RECOMMENDATION,
            Permission.ESCALATE_REQUEST,
            Permission.CLOSE_REQUEST,
            Permission.VIEW_AUDIT_LOG,
            Permission.MANAGE_STAFF,
        }
    ),
    StaffRole.SUPERVISOR: frozenset(
        {
            Permission.VIEW_REQUEST,
            Permission.ACCEPT_RECOMMENDATION,
            Permission.MODIFY_RECOMMENDATION,
            Permission.ESCALATE_REQUEST,
            Permission.CLOSE_REQUEST,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
}


def has_permission(role: StaffRole, permission: Permission) -> bool:
    """Centralized permission check."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def get_role_permissions(role: StaffRole) -> frozenset[Permission]:
    """All permissions granted to a role."""
    return ROLE_PERMISSIONS.get(role, frozenset())
