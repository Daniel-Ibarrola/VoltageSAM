import json
import os
from typing import Callable

import pytest

from .lambda_args import generate_event, get_context
from tests.unit.table import REPORTS_TABLE_NAME, LAST_REPORTS_TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["REPORTS_TABLE"] = REPORTS_TABLE_NAME
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
        from src.list_reports.list_reports import lambda_handler
        return lambda_handler

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_reports_happy_path(self, station_fixture):
        handler = self.get_handler()
        event = generate_event({"station": station_fixture})

        lambda_output = handler(event, get_context())
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data["reports"] == [
            {"station": station_fixture, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
            {"station": station_fixture, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
        ]

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_not_found(self):
        handler = self.get_handler()
        event = generate_event({"station": "Caracol"})
        context = get_context()

        lambda_output = handler(event, context)
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 404
        assert data["message"] == "Station 'Caracol' not found"

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_no_station_passed(self):
        handler = self.get_handler()
        event = generate_event()
        context = get_context()
        lambda_output = handler(event, context)
        assert lambda_output["statusCode"] == 400

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_get_reports_from_starting_date(self, station_fixture):
        handler = self.get_handler()
        event = generate_event(
            path_params={"station": station_fixture},
            query_string_params={"start_date": "2023-02-23T00:00:00"}
        )
        context = get_context()

        lambda_output = handler(event, context)
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 200
        assert data["reports"] == [
            {"station": station_fixture, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]
