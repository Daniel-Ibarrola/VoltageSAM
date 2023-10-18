from datetime import datetime
import os
import time

import boto3
import pytest
import requests


class TestApiGateway:

    station = "tonalapa"
    api_host = os.environ.get("API_HOST", "localhost").lower()

    @staticmethod
    def cloud_formation_stacks(stack_name: str):
        if stack_name is None:
            raise ValueError('Please set the AWS_SAM_STACK_NAME environment variable to the name of your stack')

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        return response["stacks"]

    def get_aws_api_url(self) -> str:
        """ Get the API Gateway URL from Cloudformation Stack outputs

            Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
        """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        stacks = self.cloud_formation_stacks(stack_name)

        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "HelloWorldApi"]

        if not api_outputs:
            raise ValueError(f"VoltageAPI not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]  # Extract url from stack outputs

    def get_aws_dynamo_db_table(self) -> str:
        """ Get the DynamoDB table name from Cloudformation Stack outputs

            Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
        """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        stacks = self.cloud_formation_stacks(stack_name)

        stack_outputs = stacks[0]["Outputs"]
        dynamodb_outputs = [output for output in stack_outputs if output["OutputKey"] == "DynamoDBTableName"]

        if not dynamodb_outputs:
            raise ValueError(f"Cannot find DynamoDB table in stack {stack_name}")

        return dynamodb_outputs[0]["OutputValue"]

    @pytest.fixture()
    def api_gateway_url(self) -> str:
        """ Get the API URL. The API can be running locally or on AWS
        """
        if self.api_host == "localhost":
            return "http://localhost:3000"
        elif self.api_host == "aws":
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

    def _dynamo_db_table(self):
        if self.api_host == "localhost":
            ddb_resource = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
            return ddb_resource.Table("VoltageReportsTable")

        elif self.api_host == "aws":
            ddb_resource = boto3.resource("dynamodb")
            return ddb_resource.Table(self.get_aws_dynamo_db_table())

        raise ValueError(
            "Invalid value for env variable API_HOST. "
            "Valid values are 'aws' and 'localhost'."
        )

    @pytest.fixture()
    def dynamo_db(self) -> None:
        """ Put sample test data in dynamo db and erase it after the tests end.
        """
        table = self._dynamo_db_table()
        num_items = table.item_count

        reports = [
            {"station": self.station, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
            {"station": self.station,  "date": "2023-02-23T16:20:00",  "battery": 55.0, "panel": 60.0},
            {"station": "Piedra Grande", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0}
        ]
        for rep in reports:
            table.put_item(Item={
                "station": rep["station"],
                "date": rep["date"],
                "battery": rep["battery"],
                "panel": rep["panel"],
            })

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

    @pytest.mark.usefixtures("clean_up_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_add_new_report(self, api_gateway_url: str) -> None:
        """ Add a new report. """
        date = datetime(2023, 2, 22, 16, 20, 0)
        date_str = date.strftime("%Y/%m/%d,%H:%M:%S")
        url = f"{api_gateway_url}/reports"
        res = requests.post(url, json={
            "station": "Caracol",
            "date": date_str,
            "battery": 20.0,
            "panel": 15.5,
        })
        assert res.ok
        assert res.json() == {
            "station": "caracol", "date": date.isoformat(), "battery": 20.0, "panel": 15.5
        }

    @pytest.mark.usefixtures("dynamo_db")
    @pytest.mark.usefixtures("wait_for_api")
    def test_station_last_report(self, api_gateway_url: str):
        """ Get the last report of a station. """

        url = f"{api_gateway_url}/last_reports/{self.station}"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}

    @pytest.mark.usefixtures("dynamo_db")
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

    @pytest.mark.usefixtures("dynamo_db")
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

    @pytest.mark.usefixtures("dynamo_db")
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
