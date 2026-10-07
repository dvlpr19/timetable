"""Role-based access. Every rule is enforced here on the server; the UI only mirrors it."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role

ALL_ROLES = frozenset(Role.values)
STAFF_ROLES = frozenset({Role.ADMIN, Role.DEKANAT, Role.KAFEDRA_MUDIRI})
ADMIN_ONLY = frozenset({Role.ADMIN})


def role_of(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return Role.ADMIN
    return user.role


def is_admin(user) -> bool:
    return role_of(user) == Role.ADMIN


def is_staff_role(user) -> bool:
    return role_of(user) in STAFF_ROLES


class RolePermission(BasePermission):
    """Reads need `view.read_roles`, writes `view.write_roles`.

    Object scope (own faculty / department / self) is checked by the view's `in_scope`.
    """

    def has_permission(self, request, view) -> bool:
        role = role_of(request.user)
        if role is None:
            return False
        allowed = view.read_roles if request.method in SAFE_METHODS else view.write_roles
        extra = getattr(view, "action_roles", {}).get(getattr(view, "action", None))
        if extra is not None:
            allowed = extra
        return role in allowed

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return view.in_scope(obj)
