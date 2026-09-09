import uuid

from django.db import models

from branch.models import Branch
from common.models import BasicModel
from user.models import User

# Create your models here.

class Staff(BasicModel):
    user = models.OneToOneField(User,
        on_delete=models.CASCADE,
        related_name="staff")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateField(null=True)

    class Meta:
        db_table = "staff"



class StaffInvitation(BasicModel):
    given_name = models.CharField(null=True, blank=True)
    family_name = models.CharField(null=True, blank=True)
    email = models.EmailField()
   
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branch_invitations",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateField()

    class Meta:
        db_table = "staff_invitation"