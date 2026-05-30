import logging
from django.core.management.base import BaseCommand
from apps.rbac.models import Role, AccessRule

logger = logging.getLogger(__name__)

# Seed data exactly as defined in docs/rbac-schema.md
ROLES = [
    {"name": "admin", "description": "Full access to everything including RBAC management"},
    {"name": "manager", "description": "Manage projects and all tasks within them"},
    {"name": "developer", "description": "Work on tasks; limited to own objects outside assigned projects"},
    {"name": "viewer", "description": "Read-only across tasks and projects"},
]

# (resource, can_read, can_read_all, can_create, can_update, can_update_all, can_delete, can_delete_all)
ACCESS_RULES = {
    "admin": [
        ("task",        True, True, True, True, True, True, True),
        ("project",     True, True, True, True, True, True, True),
        ("user",        True, True, True, True, True, True, True),
        ("role",        True, True, True, True, True, True, True),
        ("access_rule", True, True, True, True, True, True, True),
    ],
    "manager": [
        ("task",        True, True, True, True, True,  True, True),
        ("project",     True, True, True, True, True,  True, True),
        ("user",        True, True, False, False, False, False, False),
        ("role",        False, False, False, False, False, False, False),
        ("access_rule", False, False, False, False, False, False, False),
    ],
    "developer": [
        ("task",        True, True, True, True, False, True, False),
        ("project",     True, True, True, True, False, False, False),
        ("user",        False, False, False, False, False, False, False),
        ("role",        False, False, False, False, False, False, False),
        ("access_rule", False, False, False, False, False, False, False),
    ],
    "viewer": [
        ("task",        False, True, False, False, False, False, False),
        ("project",     False, True, False, False, False, False, False),
        ("user",        False, False, False, False, False, False, False),
        ("role",        False, False, False, False, False, False, False),
        ("access_rule", False, False, False, False, False, False, False),
    ],
}


class Command(BaseCommand):
    help = "Seed initial roles and access rules from rbac-schema.md"

    def handle(self, *args, **kwargs) -> None:
        self.stdout.write("Seeding roles...")

        for role_data in ROLES:
            role, created = Role.objects.get_or_create(
                name=role_data["name"],
                defaults={"description": role_data["description"]},
            )
            status = "created" if created else "already exists"
            self.stdout.write(f"  Role '{role.name}': {status}")

            for rule_tuple in ACCESS_RULES[role.name]:
                resource, r, ra, c, u, ua, d, da = rule_tuple
                _, rule_created = AccessRule.objects.update_or_create(
                    role=role,
                    resource=resource,
                    defaults={
                        "can_read": r,
                        "can_read_all": ra,
                        "can_create": c,
                        "can_update": u,
                        "can_update_all": ua,
                        "can_delete": d,
                        "can_delete_all": da,
                    },
                )
                rule_status = "created" if rule_created else "updated"
                self.stdout.write(f"    AccessRule '{role.name}/{resource}': {rule_status}")

        self.stdout.write(self.style.SUCCESS("Done. Roles and access rules are ready."))
