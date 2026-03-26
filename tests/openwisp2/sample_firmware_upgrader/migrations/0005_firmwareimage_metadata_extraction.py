from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sample_firmware_upgrader", "0004_alter_firmwareimage_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="firmwareimage",
            name="extraction_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("extracted", "Extracted"),
                    ("failed", "Failed"),
                    ("manual", "Manual"),
                    ("invalid", "Invalid"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="extraction_log",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Full technical output from the extraction attempt.",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="board",
            field=models.CharField(
                blank=True,
                default="",
                help_text='Human-readable device name e.g. "GL.iNet GL-AP1300".',
                max_length=200,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="compatible",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of compatible strings e.g. ["glinet,gl-ap1300"].',
            ),
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="fw_target",
            field=models.CharField(
                blank=True,
                default="",
                help_text='OpenWrt target/subtarget e.g. "ipq40xx/generic".',
                max_length=100,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="fw_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text='OpenWrt version e.g. "23.05.5".',
                max_length=50,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="firmwareimage",
            name="extraction_source",
            field=models.CharField(
                blank=True,
                default="",
                help_text="How metadata was obtained: fwtool, dtb, or manual.",
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
