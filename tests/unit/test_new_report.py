from datetime import datetime
import json
import os
from typing import Callable

import boto3
from boto3.dynamodb.conditions import Key
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

    @staticmethod
    def check_report(table, station: str, date: str) -> None:
        res = table.query(
            KeyConditionExpression=Key("station").eq(station.lower()) & Key("date").eq(date)
        )
        assert len(res["Items"]) == 1

        report = res["Items"][0]
        assert report["station"] == "caracol"
        assert report["date"] == date

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_station_reports_happy_path(self):
        station = "Caracol"
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")
        date_iso = date.isoformat()

        handler = self.get_handler()
        event = generate_event(body={"station": station, "date": date_str, "battery": 20.0, "panel": 15.5})
        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 201
        assert data == {"station": "caracol", "date": date_iso, "battery": 20.0, "panel": 15.5}

        # Check that last reports abd reports table were updated
        mock_dynamo = boto3.resource("dynamodb")
        reports_tb = mock_dynamo.Table(REPORTS_TABLE_NAME)
        last_reports_tb = mock_dynamo.Table(LAST_REPORTS_TABLE_NAME)

        self.check_report(reports_tb, station, date_iso)
        self.check_report(last_reports_tb, station, date_iso)

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_event_with_no_body(self):
        handler = self.get_handler()
        event = generate_event()

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 400
        assert data["message"] == "Need to pass the body with the new report parameters"

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_incomplete_report_parameters(self):
        handler = self.get_handler()
        date = "2023-10-30T17:05:03"
        event = generate_event(body={"station": "tonalapa", "date": date})

        lambda_output = handler(event, "")
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 400
        msg = data["message"]
        assert msg == "The new report must include station, date, report and panel attributes"
