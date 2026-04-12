# tests/test_snowflake.py
import pytest
from app.db import test_connection, execute_query


class TestConnection:
    def test_connection_succeeds(self):
        assert test_connection() is True

    def test_simple_query(self):
        result = execute_query("SELECT 1 AS test")
        assert result["error"] is None
        assert result["rows"][0][0] == 1

    def test_metadata_accessible(self):
        result = execute_query(
            'SELECT COUNT(*) FROM "2019_METADATA_CBG_FIELD_DESCRIPTIONS"'
        )
        assert result["error"] is None
        assert result["rows"][0][0] == 8120

    def test_fips_accessible(self):
        result = execute_query(
            'SELECT COUNT(*) FROM "2019_METADATA_CBG_FIPS_CODES"'
        )
        assert result["error"] is None
        assert result["rows"][0][0] > 3000

    def test_cbg_data_accessible(self):
        result = execute_query(
            'SELECT COUNT(*) FROM "2019_CBG_B19"'
        )
        assert result["error"] is None
        assert result["rows"][0][0] > 200000

    def test_handles_bad_query(self):
        result = execute_query("SELECT * FROM nonexistent_table_xyz")
        assert result["error"] is not None
        assert result["rows"] is None

    def test_california_income_query(self):
        """Verified query — we know this returns ~$84,261"""
        result = execute_query("""
            SELECT SUM("B19013e1" * "B19001e1") / NULLIF(SUM("B19001e1"), 0)
            FROM "2019_CBG_B19"
            WHERE LEFT("CENSUS_BLOCK_GROUP", 2) = '06'
            AND "B19013e1" IS NOT NULL
            AND "B19001e1" > 0
        """)
        assert result["error"] is None
        income = float(result["rows"][0][0])
        assert 80000 < income < 90000

    def test_fips_join_pattern(self):
        """Verify FIPS join returns correct state data"""
        result = execute_query("""
            SELECT f.STATE, COUNT(*) as cbg_count
            FROM "2019_CBG_B01" d
            JOIN "2019_METADATA_CBG_FIPS_CODES" f
                ON LEFT(d."CENSUS_BLOCK_GROUP", 2) = f.STATE_FIPS
                AND SUBSTRING(d."CENSUS_BLOCK_GROUP", 3, 3) = f.COUNTY_FIPS
            WHERE f.STATE = 'CA'
            GROUP BY f.STATE
        """)
        assert result["error"] is None
        assert result["rows"][0][0] == 'CA'
        assert result["rows"][0][1] > 1000