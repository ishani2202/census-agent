# tests/test_normalization.py
import pytest
from app.planner import normalize_state


class TestStateNormalization:
    def test_full_name_to_abbrev(self):
        assert normalize_state("California") == "CA"
        assert normalize_state("Texas") == "TX"
        assert normalize_state("New York") == "NY"
        assert normalize_state("Florida") == "FL"

    def test_lowercase_full_name(self):
        assert normalize_state("california") == "CA"
        assert normalize_state("new york") == "NY"
        assert normalize_state("texas") == "TX"

    def test_already_abbreviated(self):
        assert normalize_state("CA") == "CA"
        assert normalize_state("TX") == "TX"
        assert normalize_state("NY") == "NY"

    def test_lowercase_abbrev(self):
        assert normalize_state("ca") == "CA"
        assert normalize_state("tx") == "TX"

    def test_dc(self):
        assert normalize_state("washington dc") == "DC"
        assert normalize_state("district of columbia") == "DC"

    def test_unknown_returns_original(self):
        result = normalize_state("unknown place")
        assert result == "unknown place"

    def test_empty_string(self):
        result = normalize_state("")
        assert result == ""