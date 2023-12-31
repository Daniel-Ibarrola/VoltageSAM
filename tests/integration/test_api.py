from datetime import datetime
import time
from typing import Literal

import boto3
from boto3.dynamodb.conditions import Key
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
        raise ValueError(f"Invalid API host {host}. Host must be one of {choices}")
    return host


def wait_for(url: str, name: str) -> None:
    """ Try to connect to the given url for 5 seconds.
    """
    start = time.time()
    while time.time() - start < 5:
        try:
            requests.get(url)
            return
        except requests.ConnectionError:
            continue
    pytest.fail(f"Could not connect to {name} at {url}")


@pytest.fixture(scope="class")
def dynamo_db_tables(api_host) -> tuple:
    """ Get the DynamoDB tables
    """
    if api_host == "aws":
        reports_tn = "voltage-dev-ReportsTable-YFR5XT9RWVJQ"
        last_reports_tn = "voltage-dev-LastReportsTable-H1EEWTXUI42"
        ddb_resource = boto3.resource("dynamodb")
        reports_table = ddb_resource.Table(reports_tn)
        last_table = ddb_resource.Table(last_reports_tn)
    else:
        wait_for("http://localhost:8000", "Local DynamoDB")
        reports_tn = "VoltageReportsTableLocal"
        last_reports_tn = "VoltageLastReportsLocal"
        ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
        reports_table = create_table_if_not_exist(ddb_resource, reports_tn, api_host)
        last_table = create_table_if_not_exist(ddb_resource, last_reports_tn, api_host)

    return reports_table, last_table


class TestApiGateway:

    @pytest.fixture(autouse=True)
    def set_up_api_test(self, api_host):
        self.station = "Pto Bálsamo"
        self.client = APIClient(api_host)
        self.client.get_auth_token()

    @pytest.fixture(autouse=True)
    def wait_for_api(self):
        """ Try to connect to the API. If it is not possible after 10 seconds
            stop the tests.
        """
        wait_for(self.client.api_gateway_url, f"API")

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
                last_table.delete_item(Key={"station": rep["station"]})

        assert reports_table.item_count == report_count
        assert last_table.item_count == last_count


class TestGetStationReports(TestApiGateway):

    @pytest.mark.usefixtures("dynamo_db")
    def test_get_station_reports_happy_path(self):
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

    def test_station_not_found(self):
        response = self.client.station_reports("InvalidStation")
        assert response.status_code == 404


class TestAddNewReport(TestApiGateway):

    new_station = "Mazatán SV"

    @pytest.fixture
    def clean_up_db(self, dynamo_db_tables):
        reports_t, last_reports_t = dynamo_db_tables
        yield

        date = datetime(2023, 2, 22, 16, 20, 0).isoformat()
        reports_t.delete_item(Key={"station": self.new_station, "date": date})
        last_reports_t.delete_item(Key={"station": self.new_station})

    @pytest.mark.usefixtures("clean_up_db")
    def test_add_new_report_happy_path(self) -> None:
        """ Add a new report. """
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")
        res = self.client.new_station_report(self.new_station, date_str, 20.0, 15.5)
        assert res.status_code == 201
        assert res.json() == {
            "station": self.new_station,
            "date": date.isoformat(),
            "battery": 20.0,
            "panel": 15.5
        }

    @pytest.fixture
    def clear_reports(self, dynamo_db_tables):
        reports_t, last_reports_t = dynamo_db_tables
        yield reports_t, last_reports_t

        date1 = datetime(2023, 2, 22, 16, 20, 0)
        date2 = datetime(2023, 3, 22, 16, 20, 0)
        reports_t.delete_item(Key={"station": self.new_station, "date": date1.isoformat()})
        reports_t.delete_item(Key={"station": self.new_station, "date": date2.isoformat()})
        last_reports_t.delete_item(Key={"station": self.new_station})

    def test_last_reports_are_updated(self, clear_reports):
        date1 = datetime(2023, 2, 22, 16, 20, 0)
        date2 = datetime(2023, 3, 22, 16, 20, 0)
        date1_str = date1.strftime("%Y/%m/%d,%H:%M:%S")
        date2_str = date2.strftime("%Y/%m/%d,%H:%M:%S")

        res = self.client.new_station_report(self.new_station, date1_str, 20.0, 15.5)
        assert res.status_code == 201

        res = self.client.new_station_report(self.new_station, date2_str, 40.0, 50)
        assert res.status_code == 201

        _, last_reports_t = clear_reports
        ddb_res = last_reports_t.query(KeyConditionExpression=Key("station").eq(self.new_station))
        items = ddb_res["Items"]
        assert len(items) == 1

        assert items[0]["battery"] == 40.0
        assert items[0]["panel"] == 50.0


class TestGetStationLastReport(TestApiGateway):

    @pytest.mark.usefixtures("dynamo_db")
    def test_station_last_report_happy_path(self):
        """ Get the last report of a station. """
        response = self.client.station_last_report(self.station)
        assert response.status_code == 200
        assert response.json() == {
            "station": self.station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0
        }

    def test_station_not_found(self):
        response = self.client.station_last_report("InvalidStation")
        assert response.status_code == 404


class TestGetStationLastReports(TestApiGateway):
    @pytest.mark.usefixtures("dynamo_db")
    def test_last_reports_happy_path(self):
        """ Get the last reports of every station """
        response = self.client.last_reports()
        assert response.status_code == 200

        reports = response.json()["reports"]
        assert len(reports) == 2

        report1 = [rep for rep in reports if rep["station"] == self.station][0]
        report2 = [rep for rep in reports if rep["station"] == "Piedra Grande"][0]
        assert report1 == {
            "station": self.station,
            "date": "2023-02-23T16:20:00",
            "battery": 55.0,
            "panel": 60.0
        }
        assert report2 == {
            "station": "Piedra Grande",
            "date": "2023-02-22T16:20:00",
            "battery": 34.0,
            "panel": 40.0
        }


class TestGetStationReportCounts(TestApiGateway):

    @pytest.mark.usefixtures("dynamo_db")
    def test_get_station_reports_count_happy_path(self):
        """ Get the count of reports of a station. """
        response = self.client.station_reports_count(self.station)
        assert response.status_code == 200
        assert response.json() == {
            "reports": [
                {"date": "2023-02-23", "count": 1},
                {"date": "2023-02-22", "count": 1},
            ],
        }

    def test_station_not_found(self):
        response = self.client.station_reports_count("InvalidStation")
        assert response.status_code == 404
