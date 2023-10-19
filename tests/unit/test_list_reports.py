import json
import os
from typing import Callable

import boto3
from moto import mock_dynamodb
import pytest

from .event import generate_event
from tests.fill_table import fill_table

# Set the table name variable before importing lambda function to avoid raising an error
table_name = "test_table"
os.environ["DYNAMODB_TABLE_NAME"] = table_name


class TestListReports:
    station = "tonalapa"

    @pytest.fixture
    @mock_dynamodb
    def dynamo_db(self) -> None:
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
        fill_table(table, self.station)

        yield

        table.delete()
        del os.environ["DYNAMODB_TABLE_NAME"]

    def get_handler(self) -> Callable:
        """ Returns the lambda handler.

            Handler is imported here to make sure boto3 gets mocked
        """
        from src.list_reports.list_reports import lambda_handler
        return lambda_handler

    @pytest.mark.usefixtures("dynamo_db")
    @mock_dynamodb
    def test_station_reports_happy_path(self):
        handler = self.get_handler()
        event = generate_event({"station": self.station})
        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data == [
            {"date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]

    @pytest.mark.usefixtures("dynamo_db")
    @mock_dynamodb
    def test_station_not_found(self):
        handler = self.get_handler()
        event = generate_event({"station": "Caracol"})
        lambda_output = handler(event, "")

        assert lambda_output["statusCode"] == 404
