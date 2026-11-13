
from django.conf import settings
from django.db import models

from apps.documents.models import Document


class PerformanceReset(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="performance_resets",
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="performance_resets",
    )

    # "all" resets performance across the entire PDF.
    # Any other value represents a specific topic.
    topic = models.CharField(
        max_length=255,
        default="all",
    )

    reset_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reset_at"]

    def __str__(self):
        return (
            f"{self.student} - {self.document} "
            f"- {self.topic} - {self.reset_at}"
        )

