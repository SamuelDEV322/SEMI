from django.middleware.csrf import CsrfViewMiddleware


class DemoCsrfMiddleware(CsrfViewMiddleware):
    """Protect anonymous demo writes too; DRF exempts its dispatch by default."""

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith("/api/"):
            # The delegate has no csrf_exempt attribute. Keep Django's standard
            # cookie/token and Origin checks, including its test-client switch.
            callback = lambda request: None
        return super().process_view(request, callback, callback_args, callback_kwargs)
