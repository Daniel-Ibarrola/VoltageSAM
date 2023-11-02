from datetime import datetime
import time
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pytest
import requests

from tests.fill_table import fill_tables, create_reports_table
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
    def get_aws_dynamo_db_table() -> list[str]:
        """ Get the DynamoDB table names from AWS
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

    def create_table_if_not_exist(self, ddb_resource, table_name: str):
        """ Create a DynamoDB table if it does not exist.
        """
        table = ddb_resource.Table(table_name)

        try:
            table.item_count
        except ClientError as err:
            err_name = err.response["Error"]["Code"]
            if err_name == "ResourceNotFoundException" and self.api_host == "localhost":
                return create_reports_table(ddb_resource, table_name)
            else:
                raise ValueError("An error occurred with DynamoDB table")

        return table

    def _dynamo_db_tables(self):
        """ Get the reports and last reports tables. """
        if self.api_host == "localhost":
            ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
            reports_tn = "VoltageReportsTableLocal"
            last_reports_tn = "VoltageLastReportsLocal"
            reports_table = self.create_table_if_not_exist(ddb_resource, reports_tn)
            last_table = self.create_table_if_not_exist(ddb_resource, last_reports_tn)

        else:
            ddb_resource = boto3.resource("dynamodb")
            reports_tn, last_reports_tn = self.get_aws_dynamo_db_table()
            reports_table = ddb_resource.Table(reports_tn)
            last_table = ddb_resource.Table(last_reports_tn)

        print(f"Reports table name {reports_tn}")
        print(f"Last reports table name {last_reports_tn}")

        return reports_table, last_table

    @pytest.fixture()
    def dynamo_db(self) -> None:
        """ Put sample test data in dynamo db and erase it after the tests end.
        """
        reports_table, last_table = self._dynamo_db_tables()
        report_count = reports_table.item_count
        last_count = last_table.item_count

        reports = fill_tables(reports_table, last_table, self.station)
        print(f"Items in reports table {reports_table.item_count}")
        print(f"Items in last reports table {last_table.item_count}")

        yield

        for ii, rep in enumerate(reports):
            reports_table.delete_item(Key={
                "station": rep["station"],
                "date": rep["date"]
            })
            if ii > 0:
                last_table.delete_item(Key={
                    "station": rep["station"],
                    "date": rep["date"]
                })

        assert reports_table.item_count == report_count
        assert last_table.item_count == last_count

    @pytest.fixture
    def clean_up_db(self):
        yield
        date = datetime(2023, 2, 22, 16, 20, 0).isoformat()
        reports_t, last_reports_t = self._dynamo_db_tables()
        reports_t.delete_item(Key={
            "station": "caracol",
            "date": date
        })
        last_reports_t.delete_item(Key={
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
        assert response.json() == {
            "reports": [
                {"station": self.station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
                {"station": self.station, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            ],
            "nextKey": None
        }

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

    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_station_last_report(self):
        """ Get the last report of a station. """
        response = self.client.station_last_report(self.station)
        assert response.status_code == 200
        assert response.json() == {
            "station": self.station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0
        }

    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_last_reports(self):
        """ Get the last reports of every station """
        response = self.client.last_reports()
        assert response.status_code == 200

        reports = response.json()["reports"]
        assert len(reports) == 2

        tonalapa_rep = [rep for rep in reports if rep["station"] == "tonalapa"][0]
        piedra_rep = [rep for rep in reports if rep["station"] == "piedra grande"][0]
        assert tonalapa_rep == {
            "station": "tonalapa",
            "date": "2023-02-23T16:20:00",
            "battery": 55.0,
            "panel": 60.0
        }
        assert piedra_rep == {
            "station": "piedra grande",
            "date": "2023-02-22T16:20:00",
            "battery": 34.0,
            "panel": 40.0
        }

    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_get_station_reports_count(self):
        """ Get the count of reports of a station. """
        response = self.client.station_reports_count(self.station)
        assert response.status_code == 200
        assert response.json() == {
            "reports": [
                {"date": "2023-02-23", "count": 1},
                {"date": "2023-02-22", "count": 1},
            ],
        }
