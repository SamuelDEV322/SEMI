from django.middleware.csrf import CsrfViewMiddleware


class DemoCsrfMiddleware(CsrfViewMiddleware):
    """Protect anonymous demo writes too; DRF exempts its dispatch by default."""

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Only the marked, token-authenticated device views use device auth
        # instead of browser cookies. A URL prefix or header never bypasses CSRF.
        if getattr(callback, "semi_device_endpoint", False):
            return None
        if request.path.startswith("/api/"):
            # The delegate has no csrf_exempt attribute. Keep Django's standard
            # cookie/token and Origin checks, including its test-client switch.
            callback = lambda request: None
        return super().process_view(request, callback, callback_args, callback_kwargs)
