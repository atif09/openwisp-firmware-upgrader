from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("firmware_upgrader", "0012_update_image_type_identifiers"),
    ]

    operations = [
        migrations.AddField(
            model_name="firmwareimage",
            name="extraction_status",
            field=models.CharField(
                choices=[
                    ("unconfirmed", "Unconfirmed"),
                    ("in_progress", "In Progress"),
                    ("success", "Success"),
                    ("failed", "Failed"),
                    ("manual", "Manual"),
                    ("manually_confirmed", "Manually Confirmed"),
                    ("invalid", "Invalid"),
                ],
                db_index=True,
                default="unconfirmed",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="extraction_log",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="failure_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("unsupported_format", "Unsupported format"),
                    ("out_of_memory", "Out of memory"),
                    ("invalid_file", "Invalid file"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="board",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="compatible",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="target",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="fw_version",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="compat_version",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="source",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
