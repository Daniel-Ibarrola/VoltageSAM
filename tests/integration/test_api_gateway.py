from datetime import datetime
import os
import time

import boto3
import pytest
import requests


class TestApiGateway:

    station = "tonalapa"

    @staticmethod
    def get_aws_api_url() -> str:
        """ Get the API Gateway URL from Cloudformation Stack outputs

            Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
        """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")

        if stack_name is None:
            raise ValueError('Please set the AWS_SAM_STACK_NAME environment variable to the name of your stack')

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "HelloWorldApi"]

        if not api_outputs:
            raise KeyError(f"VoltageAPI not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]  # Extract url from stack outputs

    @pytest.fixture()
    def api_gateway_url(self) -> str:
        """ Get the API URL. The API can be running locally or on AWS
        """
        api_host = os.environ.get("API_HOST", "localhost").lower()
        if api_host == "localhost":
            return "http://localhost:3000"
        elif api_host == "aws":
            return self.get_aws_api_url()
        else:
            pytest.fail(
                "Invalid value for env variable API_HOST. "
                "Valid values are 'aws' and 'localhost'."
            )

    @pytest.fixture
    def wait_for_api(self, api_gateway_url: str):
        """ Try to connect to the API. If it is not possible after 10 seconds
            stop the tests.
        """
        start = time.time()
        while time.time() - start < 10:
            try:
                requests.get(api_gateway_url)
                return
            except requests.ConnectionError:
                continue
        pytest.fail("Could not connect to API")

    @pytest.fixture()
    def add_reports(self, api_gateway_url: str) -> None:
        d_form = "%Y/%m/%d,%H:%M:%S"
        dates = [
            datetime(2023, 2, 22, 16, 20, 0).strftime(d_form),
            datetime(2023, 2, 23, 16, 20, 0).strftime(d_form),
            datetime(2023, 2, 22, 16, 20, 0).strftime(d_form),
        ]
        reports = [
            {"station": self.station, "battery": 45.0, "panel": 68.0},
            {"station": self.station, "battery": 55.0, "panel": 60.0},
            {"station": "Piedra Grande", "battery": 34.0, "panel": 40.0}
        ]

        url = f"{api_gateway_url}/reports"
        for ii, rep in enumerate(reports):
            res = requests.post(url, json={
                "station": rep["station"],
                "date": dates[ii],
                "battery": rep["battery"],
                "panel": rep["panel"]
            })
            assert res.ok

    @pytest.mark.usefixtures("add_reports")
    @pytest.mark.usefixtures("wait_for_api")
    def test_station_last_report(self, api_gateway_url: str):
        """ Get the last report of a station """

        url = f"{api_gateway_url}/last_reports/{self.station}"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}

    @pytest.mark.usefixtures("add_reports")
    @pytest.mark.usefixtures("wait_for_api")
    def test_last_reports(self, api_gateway_url: str):
        """ Get the last reports of every station """
        url = f"{api_gateway_url}/last_reports"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == [
            {"station": "tonalapa", "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"station": "piedra grande", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]

    @pytest.mark.usefixtures("add_reports")
    @pytest.mark.usefixtures("wait_for_api")
    def test_get_station_reports(self, api_gateway_url: str):
        """ Get the reports of a station. """
        url = f"{api_gateway_url}/reports/{self.station}"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == [
            {"date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        ]

    @pytest.mark.usefixtures("add_reports")
    @pytest.mark.usefixtures("wait_for_api")
    def test_get_station_reports_count(self, api_gateway_url: str):
        """ Get the count of reports of a station. """
        url = f"{api_gateway_url}/reports/{self.station}/count"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == [
            {"date": "2023-02-22", "count": 1},
            {"date": "2023-02-23", "count": 1},
        ]
