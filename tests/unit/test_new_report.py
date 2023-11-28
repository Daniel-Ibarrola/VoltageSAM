from datetime import datetime
import json
import os
from typing import Callable

import boto3
from boto3.dynamodb.conditions import Key
import pytest

from .lambda_args import generate_event, get_context
from tests.unit.table import REPORTS_TABLE_NAME, LAST_REPORTS_TABLE_NAME

# Set the table name variable before importing lambda function to avoid raising an error
os.environ["REPORTS_TABLE"] = REPORTS_TABLE_NAME
os.environ["LAST_REPORTS_TABLE"] = LAST_REPORTS_TABLE_NAME


class TestAddNewReport:
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
    def test_add_new_report_happy_path(self):
        station = "Caracol"
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")
        date_iso = date.isoformat()

        handler = self.get_handler()
        event = generate_event(body={"station": station, "date": date_str, "battery": 20.0, "panel": 15.5})
        context = get_context()
        lambda_output = handler(event, context)
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
    def test_last_reports_are_updated(self):
        date1 = datetime(2023, 2, 22, 16, 20, 0)
        date2 = datetime(2023, 3, 22, 16, 20, 0)
        date1_str = date1.strftime("%Y/%m/%d,%H:%M:%S")
        date2_str = date2.strftime("%Y/%m/%d,%H:%M:%S")
        station = "Caracol"

        event1 = generate_event(body={"station": station, "date": date1_str, "battery": 20.0, "panel": 15.5})
        event2 = generate_event(body={"station": station, "date": date2_str, "battery": 50.0, "panel": 30.0})
        context = get_context()

        handler = self.get_handler()
        output1 = handler(event1, context)
        output2 = handler(event2, context)

        assert output1["statusCode"] == 201
        assert output2["statusCode"] == 201

        ddb_resource = boto3.resource("dynamodb")
        reports_tb = ddb_resource.Table(REPORTS_TABLE_NAME)
        last_reports_tb = ddb_resource.Table(LAST_REPORTS_TABLE_NAME)

        ddb_res = reports_tb.query(KeyConditionExpression=Key("station").eq(station.lower()))
        assert len(ddb_res["Items"]) == 2

        ddb_res = last_reports_tb.query(KeyConditionExpression=Key("station").eq(station.lower()))
        items = ddb_res["Items"]
        assert len(items) == 1
        report = items[0]

        assert report == {
            "station": station.lower(), "date": date2.isoformat(), "battery": 50.0, "panel": 30.0
        }

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_event_with_no_body(self):
        handler = self.get_handler()
        event = generate_event()
        context = get_context()

        lambda_output = handler(event, context)
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 400
        assert data["message"] == "Need to pass the body with the new report parameters"

    @pytest.mark.usefixtures("mock_dynamo_db")
    def test_incomplete_report_parameters(self):
        handler = self.get_handler()
        date = "2023-10-30T17:05:03"
        event = generate_event(body={"station": "tonalapa", "date": date})
        context = get_context()

        lambda_output = handler(event, context)
        data = json.loads(lambda_output["body"])

        assert lambda_output["statusCode"] == 400
        msg = data["message"]
        assert msg == "The new report must include station, date, report and panel attributes"
