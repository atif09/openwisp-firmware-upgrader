from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save)
def trigger_firmware_metadata_extraction(sender, instance, created, **kwargs):
    from .swapper import load_model

    try:
        FirmwareImage = load_model("FirmwareImage")
    except Exception:
        return
    if not isinstance(instance, FirmwareImage):
        return
    if not created or instance.extraction_status != FirmwareImage.STATUS_UNCONFIRMED:
        return
    from .tasks import extract_firmware_metadata

    transaction.on_commit(lambda: extract_firmware_metadata.delay(instance.pk))
