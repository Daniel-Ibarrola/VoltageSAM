import boto3
from moto import mock_dynamodb
import pytest
import os

from tests.ddb_table import fill_tables, create_reports_table
from tests.unit.table import REPORTS_TABLE_NAME, LAST_REPORTS_TABLE_NAME


@pytest.fixture
def station_fixture() -> str:
    return "Tonalapa"


@pytest.fixture
def mock_dynamo_db(station_fixture: str) -> None:
    """ Fixture creates a mock DynamoDB table with three items.

        All tests using this fixture will have DynamoDB mocked.
    """
    os.environ["REPORTS_TABLE"] = REPORTS_TABLE_NAME
    os.environ["LAST_REPORTS_TABLE"] = LAST_REPORTS_TABLE_NAME

    with mock_dynamodb():
        mock_dynamo = boto3.resource("dynamodb")
        reports_table = create_reports_table(mock_dynamo, REPORTS_TABLE_NAME)
        last_reports_table = create_reports_table(mock_dynamo, LAST_REPORTS_TABLE_NAME)

        fill_tables(reports_table, last_reports_table, station_fixture)

        yield

        reports_table.delete()
        last_reports_table.delete()
        del os.environ["REPORTS_TABLE"]
        del os.environ["LAST_REPORTS_TABLE"]
