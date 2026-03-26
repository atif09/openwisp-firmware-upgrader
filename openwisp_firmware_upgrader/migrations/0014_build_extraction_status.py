from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("firmware_upgrader", "0013_firmwareimage_metadata_extraction"),
    ]

    operations = [
        migrations.AddField(
            model_name="build",
            name="status",
            field=models.CharField(
                choices=[
                    ("analyzing", "Analyzing"),
                    ("success", "Success"),
                    ("failed", "Failed"),
                    ("invalid", "Invalid"),
                    ("manually_confirmed", "Manually confirmed"),
                ],
                db_index=True,
                default="analyzing",
                max_length=20,
                verbose_name="extraction status",
            ),
        ),
    ]
