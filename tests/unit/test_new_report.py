from datetime import datetime
import json
import os
from typing import Callable

import pytest

from .event import generate_event
from tests.unit.table import REPORTS_TABLE_NAME, LAST_REPORTS_TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["DYNAMODB_TABLE_NAME"] = REPORTS_TABLE_NAME
os.environ["LAST_REPORTS_TABLE"] = LAST_REPORTS_TABLE_NAME


class TestListReports:
    """ Class for unit testing the lambda function that returns the
        reports of a station.
    """
    @staticmethod
    def get_handler() -> Callable:
        """ Returns the lambda handler.

            Handler is imported here to make sure boto3 gets mocked
        """
        from src.new_report.new_report import lambda_handler
        return lambda_handler

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_reports_happy_path(self, station_fixture):
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")

        handler = self.get_handler()
        event = generate_event(body={"station": "Caracol", "date": date_str, "battery": 20.0, "panel": 15.5})
        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 201
        assert data == {"station": "caracol", "date": date.isoformat(), "battery": 20.0, "panel": 15.5}

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_report_already_exists(self, station_fixture):
        report = {"station": station_fixture, "date": "2023/02/22,16:20:00", "battery": 45.0, "panel": 68.0}
        handler = self.get_handler()
        event = generate_event(body=report)

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 400
        assert data["message"] == "Report for the given station and date already exists."
