from urllib.parse import urlparse


class CaptureTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = request.GET.get("tenant")

        # request.session["is_public"] = False
        # request.session["auth_tenant"] = None
       
        referer = request.META.get("HTTP_REFERER")
        if referer:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            request.session["auth_origin"] = origin
        if tenant:
            request.session["auth_tenant"] = tenant
        return self.get_response(request)
