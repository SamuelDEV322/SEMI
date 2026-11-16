from django.db import migrations


def preserve(apps, schema_editor):
    Point = apps.get_model("agriculture", "SamplingPoint")
    Plot = apps.get_model("agriculture", "Plot")
    if Point.objects.exists():
        plot = Plot.objects.create(name="Mi terreno", completed=True, step=7)
        for i, p in enumerate(Point.objects.order_by("id"), 1):
            p.plot = plot
            p.code = f"P{i}"
            p.save(update_fields=["plot", "code"])


class Migration(migrations.Migration):
    dependencies = [
        ("agriculture", "0003_plot_samplingpoint_code_samplingpoint_plot_and_more")
    ]
    operations = [migrations.RunPython(preserve, migrations.RunPython.noop)]
