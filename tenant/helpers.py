from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password, identify_hasher

from tenant.models import Client


def _is_already_hashed(password: str) -> bool:
    try:
        identify_hasher(password)
        return True
    except ValueError:
        return False


def hash_client_password(password:str):
    if password and not _is_already_hashed(password):
        return make_password(password)
    return password