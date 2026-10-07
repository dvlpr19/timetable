from django.db import transaction
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from .permissions import ADMIN_ONLY, ALL_ROLES, RolePermission, is_admin


class RoleModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet with role-based read/write access and object scope.

    Subclasses narrow `read_roles` / `write_roles` and override `in_scope` (may this user
    change this object?) and `scope_queryset` (which rows may this user see?).
    """

    permission_classes = [RolePermission]
    read_roles = ALL_ROLES
    write_roles = ADMIN_ONLY

    def in_scope(self, obj) -> bool:
        return is_admin(self.request.user)

    def scope_queryset(self, qs):
        return qs

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            if not self.in_scope(instance):
                raise PermissionDenied()

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            if not self.in_scope(instance):
                raise PermissionDenied()
