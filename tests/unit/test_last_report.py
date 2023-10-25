import json
import os
from typing import Callable

from aws_lambda_powertools.utilities.validation import validate
import pytest

from .event import generate_event
from src.last_report.schema import OUTPUT_SCHEMA
from tests.unit.table import TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["DYNAMODB_TABLE_NAME"] = TABLE_NAME


class TestListReports:
    """ Class for unit testing the lambda function that returns the
        last report of a station.
    """

    @staticmethod
    def get_handler() -> Callable:
        """ Returns the lambda handler.

            Handler is imported here to make sure boto3 gets mocked
        """
        from src.last_report.last_report import lambda_handler
        return lambda_handler

    def test_station_last_report_happy_path(self, station_fixture):
        handler = self.get_handler()
        event = generate_event({"station": station_fixture})
        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data == {"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_not_found(self):
        handler = self.get_handler()
        event = generate_event({"station": "Caracol"})
        lambda_output = handler(event, "")

        assert lambda_output["statusCode"] == 404
        assert lambda_output["body"]["message"] == "Station 'Caracol' not found"


def test_schema_validation():
    event = {
        "statusCode": 200,
        "body": json.dumps({
            "date": "2023-02-23T16:20:00",
            "battery": 55.0,
            "panel": 60.0
        }),
    }
    validate(event, schema=OUTPUT_SCHEMA)  # should not raise
