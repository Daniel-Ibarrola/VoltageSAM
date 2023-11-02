import json
import os
from typing import Callable

import pytest

from .event import generate_event
from tests.unit.table import REPORTS_TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["DYNAMODB_TABLE_NAME"] = REPORTS_TABLE_NAME


class TestReportCounts:
    """ Class for unit testing the lambda function that returns the
        last report of a station.
    """

    @staticmethod
    def get_handler() -> Callable:
        """ Returns the lambda handler.

            Handler is imported here to make sure boto3 gets mocked
        """
        from src.report_counts.report_counts import lambda_handler
        return lambda_handler

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_report_count_happy_path(self, station_fixture):
        handler = self.get_handler()
        event = generate_event({"station": station_fixture})

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data["reports"] == [
                {"date": "2023-02-23", "count": 1},
                {"date": "2023-02-22", "count": 1},
            ]

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_not_found(self):
        handler = self.get_handler()
        event = generate_event({"station": "Caracol"})

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 404
        assert data["message"] == "Station 'Caracol' not found"
