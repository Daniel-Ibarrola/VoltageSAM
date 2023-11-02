from datetime import datetime
import time
from typing import Literal

import boto3
from dotenv import load_dotenv
import pytest
import requests

from tests.ddb_table import fill_tables, create_table_if_not_exist
from tests.integration.client import APIClient
from tests.integration.env import get_env_var


load_dotenv()


@pytest.fixture(scope="class")
def api_host() -> Literal["localhost", "aws"]:
    host = get_env_var("API_HOST", "localhost").lower()
    choices = {"localhost", "aws"}
    if host not in choices:
        raise ValueError(f"Invalid API hot {host}. Host must be one of {choices}")
    return host


@pytest.fixture(scope="class")
def dynamo_db_tables(api_host) -> tuple:
    """ Get the DynamoDB tables
    """
    if api_host == "aws":
        reports_tn = "VoltageReportsTable"
        last_reports_tn = "VoltageLastReportsTable"
        ddb_resource = boto3.resource("dynamodb")
        reports_table = create_table_if_not_exist(ddb_resource, reports_tn, api_host)
        last_table = create_table_if_not_exist(ddb_resource, last_reports_tn, api_host)
    else:
        ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
        reports_table = ddb_resource.Table("VoltageReportsTableLocal")
        last_table = ddb_resource.Table("VoltageLastReportsLocal")

    return reports_table, last_table


class TestApiGateway:

    @pytest.fixture(autouse=True)
    def set_up_api_test(self, api_host):
        self.station = "tonalapa"
        self.client = APIClient(api_host)
        self.client.get_auth_token()

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

    @pytest.fixture()
    def dynamo_db(self, dynamo_db_tables) -> None:
        """ Put sample test data in dynamo db and erase it after the tests end.
        """
        reports_table, last_table = dynamo_db_tables
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
    def clean_up_db(self, dynamo_db_tables):
        yield
        date = datetime(2023, 2, 22, 16, 20, 0).isoformat()
        reports_t, last_reports_t = dynamo_db_tables
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
        assert res.status_code == 201
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
