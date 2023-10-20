import json
import os
from typing import Callable

from moto import mock_dynamodb
import pytest

from .event import generate_event
from tests.fill_table import TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["DYNAMODB_TABLE_NAME"] = TABLE_NAME


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

    @mock_dynamodb
    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_last_reports_happy_path(self, station_fixture):
        handler = self.get_handler()
        event = generate_event({"station": station_fixture})
        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data == [
            {"station": "tonalapa", "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"station": "piedra grande", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]
