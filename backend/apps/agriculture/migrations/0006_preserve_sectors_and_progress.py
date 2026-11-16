from django.db import migrations


def preserve(apps, schema_editor):
    alias = schema_editor.connection.alias
    Plot = apps.get_model("agriculture", "Plot")
    Zone = apps.get_model("agriculture", "TerrainZone")
    Point = apps.get_model("agriculture", "SamplingPoint")
    Membership = apps.get_model("agriculture", "SectorMembership")
    Trial = apps.get_model("agriculture", "SurfaceTrial")
    stages = {1: 1, 2: 2, 3: 2, 4: 3, 5: 4, 6: 4, 7: 4}
    for plot in Plot.objects.using(alias).all():
        if plot.demo:
            Trial.objects.using(alias).get_or_create(
                plot_id=plot.id,
                defaults={"state": plot.surface, "conservative": plot.conservative},
            )
        plot.step = 4 if plot.completed else stages.get(plot.step, 1)
        plot.save(using=alias, update_fields=["step"])
    # Material categories are preserved byte-for-byte, but never recommended
    # as sectors in a new agricultural setup.
    Zone.objects.using(alias).filter(category__in=["sand", "other"]).update(
        archived=True, historical_surface=True
    )
    for point in Point.objects.using(alias).exclude(zone_id=None):
        Membership.objects.using(alias).get_or_create(
            point_id=point.id, zone_id=point.zone_id
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "agriculture",
            "0005_terrainzone_archived_terrainzone_historical_surface_and_more",
        )
    ]
    operations = [migrations.RunPython(preserve, migrations.RunPython.noop)]
