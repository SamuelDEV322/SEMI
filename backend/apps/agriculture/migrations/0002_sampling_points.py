from django.db import migrations, models
import django.db.models.deletion


def associate_safe_labels(apps, schema_editor):
    Sample = apps.get_model("agriculture", "Sample")
    Point = apps.get_model("agriculture", "SamplingPoint")
    for label in (
        Sample.objects.order_by().values_list("point_label", flat=True).distinct()
    ):
        if not label or not label.strip():
            continue
        rows = Sample.objects.filter(point_label=label)
        positions = set(
            rows.filter(
                position_method="manual_schematic", x__isnull=False, y__isnull=False
            ).values_list("x", "y")
        )
        # Conflicting historical positions are deliberately left unassociated.
        if len(positions) > 1:
            continue
        coords = next(iter(positions)) if positions else (None, None)
        if any(v is not None and not 0 <= v <= 100 for v in coords):
            continue
        point = Point.objects.create(
            name=label,
            position_method="manual_schematic" if positions else "none",
            x=coords[0],
            y=coords[1],
        )
        rows.update(sampling_point=point)


class Migration(migrations.Migration):
    dependencies = [("agriculture", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="SamplingPoint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=60, unique=True)),
                ("position_method", models.CharField(default="none", max_length=24)),
                ("x", models.FloatField(blank=True, null=True)),
                ("y", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddField(
            model_name="sample",
            name="sampling_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="samples",
                to="agriculture.samplingpoint",
            ),
        ),
        migrations.RunPython(associate_safe_labels, migrations.RunPython.noop),
    ]
