import pytest
from backend.services.diff_service import unified_diff, diff_stats

ORIGINAL = 'resource "oci_core_vcn" "main" {\n  cidr_block = "10.0.0.0/16"\n}'
MODIFIED = 'resource "oci_core_vcn" "main" {\n  cidr_block   = "10.0.0.0/16"\n  display_name = "proviso-vcn"\n}'


def test_unified_diff_detects_changes():
    lines = unified_diff(ORIGINAL, MODIFIED)
    assert any(l.startswith("+") for l in lines)


def test_no_diff_for_identical():
    lines = unified_diff(ORIGINAL, ORIGINAL)
    assert lines == []


def test_diff_stats():
    stats = diff_stats(ORIGINAL, MODIFIED)
    assert stats["lines_added"] > 0
    assert stats["total_changes"] > 0
