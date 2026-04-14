import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "qaop-metadata.schema.json"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def validator(schema):
    return Draft202012Validator(schema)


@pytest.fixture
def valid_cisplatin():
    return json.loads((FIXTURES_DIR / "valid-cisplatin-aop472.json").read_text())
