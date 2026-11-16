from django.db import models


class SystemEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=32)
    message = models.CharField(max_length=240)
    source = models.CharField(max_length=12, default="mock", editable=False)

    class Meta:
        ordering = ["-created_at", "-id"]
