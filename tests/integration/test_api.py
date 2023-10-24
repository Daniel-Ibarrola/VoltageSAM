from datetime import datetime
import time
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pytest
import requests

from tests.fill_table import fill_table
from tests.integration.client import APIClient
from tests.integration.env import get_env_var


load_dotenv()


class TestApiGateway:

    def setup_method(self, method):
        self.station = "tonalapa"
        self.api_host = self.get_api_host()
        self.client = APIClient(self.api_host)

    @staticmethod
    def get_api_host() -> Literal["localhost", "aws"]:
        host = get_env_var("API_HOST", "localhost").lower()
        choices = {"localhost", "aws"}
        if host not in choices:
            raise ValueError(f"Invalid API hot {host}. Host must be one of {choices}")
        return host

    @staticmethod
    def get_aws_dynamo_db_table() -> str:
        """ Get the DynamoDB table name from AWS
        """
        ddb = boto3.client("dynamodb")
        response = ddb.list_tables()
        table_names = [tb for tb in response["TableNames"] if "voltage" in tb.lower()]

        if not table_names:
            raise ValueError(f"Cannot find DynamoDB table")
        return table_names[0]

    @pytest.fixture
    def wait_for_api(self):
        """ Try to connect to the API. If it is not possible after 10 seconds
            stop the tests.
        """
        start = time.time()
        while time.time() - start < 10:
            try:
                requests.get(self.client.api_gateway_url)
                return
            except requests.ConnectionError:
                continue
        pytest.fail("Could not connect to API")

    def _dynamo_db_table(self):
        if self.api_host == "localhost":
            ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
            table_name = "VoltageReportsTableLocal"
            table = ddb_resource.Table(table_name)

        else:
            ddb_resource = boto3.resource("dynamodb")
            table_name = self.get_aws_dynamo_db_table()
            table = ddb_resource.Table(table_name)

        print(f"Table {table_name}")

        try:
            table.item_count
        except ClientError as err:
            err_name = err.response["Error"]["Code"]
            if err_name == "ResourceNotFoundException" and self.api_host == "localhost":
                ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
                table = ddb_resource.create_table(
                    TableName="VoltageReportsTableLocal",
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
            else:
                raise ValueError("An error occurred with DynamoDB table")

        return table

    @pytest.fixture()
    def dynamo_db(self) -> None:
        """ Put sample test data in dynamo db and erase it after the tests end.
        """
        table = self._dynamo_db_table()
        num_items = table.item_count

        reports = fill_table(table, self.station)
        print(f"Items in table {table.item_count}")

        yield

        for rep in reports:
            table.delete_item(Key={
                "station": rep["station"],
                "date": rep["date"]
            })

        assert table.item_count == num_items

    @pytest.fixture
    def clean_up_db(self):
        yield
        date = datetime(2023, 2, 22, 16, 20, 0).isoformat()
        table = self._dynamo_db_table()
        table.delete_item(Key={
            "station": "caracol",
            "date": date
        })

    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_get_station_reports(self):
        """ Get the reports of a station.
        """
        response = self.client.station_reports(self.station)
        assert response.status_code == 200
        assert response.json() == [
            {"station": self.station, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"station": self.station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]

    @pytest.mark.skip(reason="Endpoint not implemented yet")
    @pytest.mark.usefixtures("clean_up_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_add_new_report(self) -> None:
        """ Add a new report. """
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")
        res = self.client.new_station_report("Caracol", date_str, 20.0, 15.5)
        assert res.ok
        assert res.json() == {
            "station": "caracol", "date": date.isoformat(), "battery": 20.0, "panel": 15.5
        }

    @pytest.mark.skip(reason="Endpoint not implemented yet")
    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_station_last_report(self):
        """ Get the last report of a station. """
        response = self.client.station_last_report(self.station)
        assert response.status_code == 200
        assert response.json() == {
            "station": self.station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0
        }

    @pytest.mark.skip(reason="Endpoint not implemented yet")
    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_last_reports(self):
        """ Get the last reports of every station """
        response = self.client.last_reports()
        assert response.status_code == 200
        assert response.json() == [
            {"station": "tonalapa", "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"station": "piedra grande", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]

    @pytest.mark.skip(reason="Endpoint not implemented yet")
    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_get_station_reports_count(self):
        """ Get the count of reports of a station. """
        response = self.client.station_reports_count(self.station)
        assert response.status_code == 200
        assert response.json() == [
            {"date": "2023-02-22", "count": 1},
            {"date": "2023-02-23", "count": 1},
        ]
