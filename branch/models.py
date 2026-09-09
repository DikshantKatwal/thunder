from django.db import models, transaction
from django.db.models import Max
from common.models import BasicModel

# Create your models here.
class Branch(BasicModel):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.CharField(max_length=30, null=True)
    status = models.BooleanField(default=True)
    address = models.TextField( null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "branch"
        ordering = ["sequence"]

    def save(self, *args, **kwargs):
        # Assign next sequence only if not provided
        if not self.sequence or self.sequence == 0:
            with transaction.atomic():
                max_sequence = (
                    Branch.objects.all().aggregate(max_seq=Max("sequence"))
                    .get("max_seq")
                )
                self.sequence = (max_sequence or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
