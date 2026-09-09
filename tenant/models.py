from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

from common.models import BasicModel

# Create your models here.

   

class Client(BasicModel, TenantMixin):
    auto_drop_schema =True
    created_on = models.DateField(auto_now_add=True)
    legal_name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    @property
    def full_name(self):
        return " ".join(
            str(part).title() for part in [self.given_name, self.family_name] if part
        )


class Domain(DomainMixin):
    is_active = models.BooleanField(default=False)

