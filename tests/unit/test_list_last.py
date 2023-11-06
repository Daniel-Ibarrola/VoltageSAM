import json
import os
from typing import Callable

import boto3
from moto import mock_dynamodb
import pytest

from .event import generate_event
from tests.ddb_table import create_reports_table
from tests.unit.table import LAST_REPORTS_TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["LAST_REPORTS_TABLE"] = LAST_REPORTS_TABLE_NAME


class TestListReports:
    """ Class for unit testing the lambda function that returns the
        last reports of all stations.
    """

    @staticmethod
    def get_handler() -> Callable:
        """ Returns the lambda handler.

            Handler is imported here to make sure boto3 gets mocked
        """
        from src.list_last.list_last import lambda_handler
        return lambda_handler

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_last_reports_happy_path(self, station_fixture):
        handler = self.get_handler()
        event = generate_event({"station": station_fixture})

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data["reports"] == [
            {"station": "tonalapa", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
            {"station": "piedra grande", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0},
        ]

    @pytest.fixture
    def last_reports_table(self) -> None:
        """ Fixture creates a mock DynamoDB table with no items.
        """
        with mock_dynamodb():
            mock_dynamo = boto3.resource("dynamodb")
            create_reports_table(mock_dynamo, LAST_REPORTS_TABLE_NAME)
            yield

    def test_no_reports(self, last_reports_table):
        handler = self.get_handler()
        event = generate_event({"station": "Caracol"})

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert len(data["reports"]) == 0
