from social_core.exceptions import AuthForbidden
from django.db import connection
from tenant.models import Client
from django.shortcuts import redirect
from decouple import config
from django.contrib.auth import logout

from user.models import User


def set_tenant_schema_context(strategy, *args, **kwargs):
    """Set tenant schema context from session"""
    tenant = strategy.session_get("auth_tenant")
    if not tenant:
        return
        # raise AuthForbidden("google-oauth2", "No tenant context found")
    try:
        connection.set_schema(tenant)
        print(f"Set schema context to: {tenant}")
        return {"tenant": tenant}

    except Client.DoesNotExist:
        print(f"Tenant with id {tenant} not found")
        raise AuthForbidden("google-oauth2", "Invalid tenant")

from django.core import signing
def send_available_accounts(strategy,tenant=None, *args, **kwargs):
    if not tenant:
        details= kwargs.get("details")
        email = details.get("email")
        token = signing.dumps(email)
        frontend_url = str(config("FRONTEND_URL"))
        redirect_url = (
            f"{frontend_url}/auth/{token}/accounts/"
        )
        return redirect(redirect_url)
    return

def finalize_login(strategy, backend, user:User=None, tenant=None, *args, **kwargs):
    # frontend_w_subdomain = strategy.session_pop("auth_origin")
    frontend_w_subdomain = str(config("SUB_DOMAIN_FRONTEND_URL"))
    frontend_w_subdomain =frontend_w_subdomain.replace("{subdomain}",tenant)
    if not user:
        redirect_url = f"{frontend_w_subdomain}/auth/"
        return redirect(redirect_url)
    request = strategy.request
    strategy.session_pop("auth_tenant")

    user.auth_provider = backend.name
    user.is_social = True
    user.save(update_fields=["auth_provider", "is_social"])
    secret_key = user.generate_temp_secret()
    redirect_url = (
        f"{frontend_w_subdomain}/auth/callback/?secret={secret_key}&email={user.email}"
    )
    logout(request)
    return redirect(redirect_url)
