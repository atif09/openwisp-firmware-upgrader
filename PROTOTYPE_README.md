# Firmware Metadata Extraction Prototype

This file explains the architectural changes and core logic implemented
for the firmware metadata extraction prototype. These changes allow
OpenWISP Firmware Upgrader to automatically extract metadata from OpenWrt
firmware images at upload time, eliminating manual metadata entry.

---

## Overview of Changes

The prototype introduces an asynchronous extraction pipeline that runs
immediately after a firmware image is uploaded. Metadata is extracted
using fwtool (primary) and DTB scanning (fallback), populating board,
compatible, target, and version fields automatically. Images remain
unconfirmed until extraction completes, preventing use in upgrades until
metadata is verified.

---

## How It Works: The Lifecycle

The system uses an asynchronous, signal-driven architecture to handle
metadata extraction without blocking the upload request.

### Trigger

When a firmware image is uploaded, magic bytes and rootfs filename checks
run synchronously. If both pass, the file is saved with
`extraction_status = unconfirmed` and a Celery task is queued.

### Background Task

`extract_firmware_metadata` runs the extraction in two steps:

- **fwtool** (primary): reads the JSON trailer from sysupgrade images.
  No decompression needed.
- **DTB scan** (fallback): if fwtool fails, decompresses the kernel and
  uses `fdt` to locate the Device Tree Blob.

### Outcomes

- Both succeed → `status = success`, metadata fields populated
- Both fail → `status = failed`, `failure_reason = unsupported_format`
- Malformed file → `status = invalid`, all fields locked

### Manual Takeover

On failure, metadata fields are unlocked in the admin. The operator fills
them in and saves. `save_model()` transitions the status directly to
`manually_confirmed`. Once confirmed, all fields become read-only.

### Build-Level Status

`_update_extraction_status()` aggregates image statuses after each
extraction. The build becomes usable for mass upgrades only when all
images reach `success` or `manually_confirmed`. A `generic_notification`
fires when the build transitions out of `analyzing`.

---

## Core File Modifications

| File | Change |
|------|--------|
| `base/models.py` | Extraction status fields on `FirmwareImage`, build-level `status` field on `AbstractBuild`, `_update_extraction_status()` aggregate, `_notify_extraction_complete()` notification |
| `extractors/base.py` | `BaseMetadataExtractor` ABC with pluggable `extract()`, `extract_from_image()`, `extract_from_dtb()` |
| `extractors/openwrt.py` | `OpenWrtMetadataExtractor` — fwtool primary path, DTB fallback, chunked decompression with `_check_limits()` |
| `extractors/exceptions.py` | `ExtractionError`, `UnsupportedImageError`, `DecompressionLimitExceeded` |
| `tasks.py` | `extract_firmware_metadata` Celery task, state machine, `_compat_blocks_pairing()` guard |
| `admin.py` | `FirmwareImageAdmin` with `get_readonly_fields()`, `save_model()`, status badges, `re_extract_metadata` action |
| `templates/.../firmwareimage_change_form.html` | Auto-refresh JS snippet when `extraction_status == in_progress` |
| `api/serializers.py` | Extraction fields marked read-only in `FirmwareImageSerializer` |
| `settings.py` | `MAX_KERNEL_BYTES`, `MAX_DECOMPRESSED_BYTES`, `MAX_DECOMPRESSED_RATIO` settings |

---

## Demo




fwtool extraction:


https://github.com/user-attachments/assets/f0b3e8a4-073c-4084-81e5-7ea8fff3b087



DTB extraction:


https://github.com/user-attachments/assets/fddef30c-3989-446a-9d95-16cf50ca48ac



## Results

Successful extraction
<img width="1233" height="885" alt="image" src="https://github.com/user-attachments/assets/463aba69-e2bc-4792-b578-d3de01bef14b" />

Failed with manual input form
<img width="1020" height="600" alt="image" src="https://github.com/user-attachments/assets/9a9a3094-8859-4347-bd0c-8dc952a799c2" />

Notifications
> On success
<img width="889" height="137" alt="image" src="https://github.com/user-attachments/assets/22f166f6-41e9-41be-b90b-aa56ac454d01" />

> On failures/warnings
<img width="887" height="288" alt="image" src="https://github.com/user-attachments/assets/74a81172-7318-493e-a66e-f3705243d0e1" />

---

## Key Features Verified

- **Upload validation**: JPEG, PNG, PDF, ZIP, and executable files rejected
  immediately via magic bytes check. `*-squashfs-rootfs.img` rejected by
  filename.
- **fwtool extraction**: board, compatible, target, fw\_version,
  compat\_version populated automatically on sysupgrade images.
- **DTB fallback**: board and compatible extracted from FIT and sdcard
  images where fwtool finds no trailer (ipq40xx, sunxi).
- **Graceful failure**: x86 and armsr fail cleanly to
  `unsupported_format`, unlocking manual input fields.
- **Manual takeover**: operator fills in metadata after failure, status
  transitions to `manually_confirmed` on save.
- **Field locking**: metadata fields become read-only after `success` or
  `manually_confirmed` at both model and admin level.
- **Build-level status**: build blocks mass upgrades until all images are
  confirmed. Adding a new image resets status to `analyzing`.
- **Notifications**: `generic_notification` sent on extraction failure
  (image-level) and on build completion (build-level), both with direct
  admin links.
- **Decompression safety**: size cap and ratio limit enforced during
  kernel decompression. `DecompressionLimitExceeded` recorded as
  `out_of_memory`.
- **Cross-version compatibility**: `compat_version > 1.0` blocks
  auto-pairing to prevent network breakage during swconfig-to-DSA
  migration.
