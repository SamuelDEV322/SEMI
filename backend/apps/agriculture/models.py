from django.db import models


class Plot(models.Model):
    name = models.CharField(max_length=80, default="Mi cafetal")
    crop = models.CharField(max_length=40, default="Coffea arabica L.", editable=False)
    demo = models.BooleanField(default=False)
    step = models.PositiveSmallIntegerField(default=1)
    completed = models.BooleanField(default=False)
    surface = models.CharField(max_length=20, default="inactive")
    conservative = models.BooleanField(default=True)


class TerrainZone(models.Model):
    plot = models.ForeignKey(Plot, on_delete=models.PROTECT, related_name="zones")
    name = models.CharField(max_length=80)
    # Retained only for historical Gate 3 rows; no agricultural API edits it.
    category = models.CharField(max_length=20, blank=True, default="", editable=False)
    archived = models.BooleanField(default=False)
    historical_surface = models.BooleanField(default=False)


class SamplingPoint(models.Model):
    plot = models.ForeignKey(
        Plot, null=True, blank=True, on_delete=models.PROTECT, related_name="points"
    )
    zone = models.ForeignKey(
        TerrainZone, null=True, blank=True, on_delete=models.PROTECT
    )
    code = models.CharField(max_length=20, blank=True)
    zone_history = models.ManyToManyField(
        TerrainZone, through="SectorMembership", related_name="historical_points"
    )
    name = models.CharField(max_length=60, unique=True)
    position_method = models.CharField(max_length=24, default="none")
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]


class Sample(models.Model):
    """One contact sample; NPK and moisture share provenance and time."""

    demo_key = models.CharField(max_length=80, unique=True, null=True, blank=True)
    sampling_point = models.ForeignKey(
        SamplingPoint,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="samples",
    )
    captured_at = models.DateTimeField()
    point_label = models.CharField(max_length=60)
    nitrogen = models.FloatField(null=True, blank=True)
    phosphorus = models.FloatField(null=True, blank=True)
    potassium = models.FloatField(null=True, blank=True)
    soil_moisture = models.FloatField(null=True, blank=True)
    npk_unit = models.CharField(max_length=12, default="mg/kg")
    moisture_unit = models.CharField(max_length=12, default="%")
    status = models.CharField(
        max_length=16,
        choices=[("valid", "Válida"), ("invalid", "Inválida")],
        default="valid",
    )
    source = models.CharField(max_length=12, default="mock", editable=False)
    position_method = models.CharField(max_length=24, default="none")
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-captured_at", "-id"]
        indexes = [models.Index(fields=["captured_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(source__in=["mock", "replay", "real"]),
                name="sample_source_known",
            )
        ]


class SectorMembership(models.Model):
    """Known associations, preserved on unlink; not a claim about sample-time position."""

    point = models.ForeignKey(SamplingPoint, on_delete=models.PROTECT)
    zone = models.ForeignKey(TerrainZone, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["point", "zone"], name="unique_known_sector_membership"
            )
        ]


class SurfaceTrial(models.Model):
    """Lab-only simulated input, independent of agricultural sector metadata."""

    plot = models.OneToOneField(
        Plot, on_delete=models.PROTECT, related_name="surface_trial"
    )
    state = models.CharField(max_length=20, default="inactive")
    conservative = models.BooleanField(default=True)
