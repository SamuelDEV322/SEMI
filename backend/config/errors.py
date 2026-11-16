from django.http import JsonResponse
from rest_framework.views import exception_handler as drf_handler


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": (
                    "validation_error"
                    if response.status_code == 400
                    else "request_error"
                ),
                "detail": response.data,
            },
            "mode": "demonstration",
        }
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "detail": "Actualiza la sesión y vuelve a intentar.",
            },
            "mode": "demonstration",
        },
        status=403,
    )
