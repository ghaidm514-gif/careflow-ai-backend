"""Role-Based Access Control (RBAC) configuration."""

from app.domain.enums import Permission, StaffRole

ROLE_PERMISSIONS = {
    StaffRole.TRIAGE_NURSE: {
        Permission.VIEW_REQUEST,
        Permission.ACCEPT_RECOMMENDATION,
        Permission.MODIFY_RECOMMENDATION,
        Permission.ESCALATE_REQUEST,
        Permission.VIEW_AUDIT_LOG,
    },
    StaffRole.ADMINISTRATOR: {
        Permission.VIEW_REQUEST,
        Permission.ACCEPT_RECOMMENDATION,
        Permission.MODIFY_RECOMMENDATION,
        Permission.ESCALATE_REQUEST,
        Permission.CLOSE_REQUEST,
        Permission.VIEW_AUDIT_LOG,
        Permission.MANAGE_STAFF,
    },
    StaffRole.SUPERVISOR: {
        Permission.VIEW_REQUEST,
        Permission.ACCEPT_RECOMMENDATION,
        Permission.MODIFY_RECOMMENDATION,
        Permission.ESCALATE_REQUEST,
        Permission.CLOSE_REQUEST,
        Permission.VIEW_AUDIT_LOG,
    },
}


def has_permission(role: StaffRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_role_permissions(role: StaffRole) -> set:
    return ROLE_PERMISSIONS.get(role, set())
