# tests/test_validator.py
import pytest
from app.validator import validate_sql, check_safety, check_syntax, ensure_limit


class TestSafety:
    def test_allows_select(self):
        result = check_safety('SELECT "B19013e1" FROM "2019_CBG_B19"')
        assert result["safe"] is True

    def test_blocks_drop(self):
        result = check_safety('DROP TABLE "2019_CBG_B19"')
        assert result["safe"] is False
        assert "DROP" in result["error"]

    def test_blocks_delete(self):
        result = check_safety('DELETE FROM "2019_CBG_B19"')
        assert result["safe"] is False

    def test_blocks_insert(self):
        result = check_safety('INSERT INTO "2019_CBG_B19" VALUES (1)')
        assert result["safe"] is False

    def test_blocks_update(self):
        result = check_safety('UPDATE "2019_CBG_B19" SET col = 1')
        assert result["safe"] is False

    def test_blocks_create(self):
        result = check_safety('CREATE TABLE test (id INT)')
        assert result["safe"] is False

    def test_blocks_truncate(self):
        result = check_safety('TRUNCATE TABLE "2019_CBG_B19"')
        assert result["safe"] is False


class TestSyntax:
    def test_valid_sql(self):
        result = check_syntax('SELECT "B19013e1" FROM "2019_CBG_B19" LIMIT 10')
        assert result["valid"] is True

    def test_invalid_sql(self):
        result = check_syntax('SELECT FROM WHERE')
        assert result["valid"] is False
        assert result["error"] is not None


class TestLimitInjection:
    def test_adds_limit_when_missing(self):
        sql = 'SELECT "B19013e1" FROM "2019_CBG_B19"'
        result = ensure_limit(sql)
        assert "LIMIT" in result.upper()

    def test_preserves_existing_limit(self):
        sql = 'SELECT "B19013e1" FROM "2019_CBG_B19" LIMIT 500'
        result = ensure_limit(sql)
        assert result == sql

    def test_no_double_limit(self):
        sql = 'SELECT "B19013e1" FROM "2019_CBG_B19" LIMIT 100'
        result = ensure_limit(sql)
        assert result.upper().count("LIMIT") == 1


class TestValidateSql:
    def test_valid_query_passes(self):
        sql = 'SELECT AVG("B19013e1") FROM "2019_CBG_B19" WHERE STATE = \'CA\''
        result = validate_sql(sql)
        assert result["valid"] is True
        assert result["error"] is None
        assert "LIMIT" in result["sql"].upper()

    def test_dangerous_query_blocked(self):
        result = validate_sql('DROP TABLE "2019_CBG_B19"')
        assert result["valid"] is False

    def test_returns_sql_with_limit(self):
        sql = 'SELECT "B19013e1" FROM "2019_CBG_B19"'
        result = validate_sql(sql)
        assert result["valid"] is True
        assert "LIMIT" in result["sql"].upper()