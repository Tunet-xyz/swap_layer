"""Admin display callbacks must render empty and populated records on Django 4–6."""

from types import SimpleNamespace

from swap_layer.storage.admin import StorageFileAdminMixin, StorageQuotaAdminMixin


def test_empty_file_display_has_safe_placeholder():
    mixin = StorageFileAdminMixin()
    record = SimpleNamespace(file_size=0, content_type=None, file_url=None, storage_provider=None)
    assert "—" in mixin.file_size_display(record)
    assert "—" in mixin.file_preview(record)
    assert "—" in mixin.file_link(record)
    assert "—" in mixin.provider_badge(record)


def test_quota_numbers_render_before_html_escaping():
    record = SimpleNamespace(
        storage_usage_percentage=lambda: 80,
        storage_used_bytes=2 * 1024**3,
        storage_quota_bytes=3 * 1024**3,
        storage_files_count=7,
    )
    mixin = StorageQuotaAdminMixin()
    assert "80.0%" in mixin.quota_usage_bar(record)
    assert "#ffc107" in mixin.quota_usage_bar(record)
    assert "2.00 GB / 3.00 GB" in mixin.storage_info(record)
    assert "7 files" in mixin.storage_info(record)
