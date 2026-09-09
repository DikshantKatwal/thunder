from django.dispatch import receiver
from django_tenants.utils import schema_context
from django_tenants.signals import post_schema_sync

from branch.models import Branch
from staff.models import Staff
from tenant.models import Client
from django.utils import timezone


@receiver(post_schema_sync)
def create_tenant_superuser(sender, tenant, **kwargs):
    if not isinstance(tenant, Client):
        return
    if tenant.schema_name == "public":
        return
    if not tenant.email or not tenant.password:
        return

    from django.contrib.auth import get_user_model
    User = get_user_model()

    with schema_context(tenant.schema_name):
        user, created_user = User.objects.get_or_create(
            email=tenant.email,
            defaults={
                "given_name": tenant.given_name or "",
                "family_name": tenant.family_name or "",
                "phone": tenant.phone,
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
            },
        )
        branch, _created_branch = Branch.objects.get_or_create(
            name="Main Branch",
        )
        Staff.objects.get_or_create(
            user=user,
            defaults={
                "branch": branch,
                "joined_at": timezone.now().date(),
            },
        )
        
        if created_user:
            user.password = tenant.password
            user.save(update_fields=["password"])
