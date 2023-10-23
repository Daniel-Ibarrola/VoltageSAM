import boto3
from moto import mock_dynamodb
import pytest
import os

from tests.fill_table import fill_table


@pytest.fixture
def station_fixture() -> str:
    return "tonalapa"


@pytest.fixture
def mock_dynamo_db(station_fixture: str) -> None:
    """ Fixture creates a mock DynamoDB table with three items.

        All tests using this fixture will have DynamoDB mocked.
    """
    table_name = "test_table"
    os.environ["DYNAMODB_TABLE_NAME"] = table_name

    with mock_dynamodb():
        mock_dynamo = boto3.resource("dynamodb")
        table = mock_dynamo.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": "station",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "date",
                    "KeyType": "RANGE"
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "station",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "date",
                    "AttributeType": "S"
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        fill_table(table, station_fixture)

        yield

        table.delete()
        del os.environ["DYNAMODB_TABLE_NAME"]
