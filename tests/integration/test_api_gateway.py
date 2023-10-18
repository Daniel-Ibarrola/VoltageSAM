import os

import boto3
import pytest
import requests


class TestApiGateway:

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
            raise KeyError(f"HelloWorldAPI not found in stack {stack_name}")

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
            pytest.fail("Invalid value for env variable API_HOST")

    def test_station_last_report(self, api_gateway_url: str):
        """ Get the last report of a station """
        station = "S160"
        url = f"{api_gateway_url}/last_reports/{station}"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"message": "Last Report"}

    def test_last_reports(self, api_gateway_url: str):
        """ Get the last reports of every station """
        url = f"{api_gateway_url}/last_reports"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"message": "List Last Reports"}

    def test_get_station_reports(self, api_gateway_url: str):
        """ Get the reports of a station. """
        station = "S160"
        url = f"{api_gateway_url}/reports/{station}"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"message": "List Station Reports"}

    def test_get_station_reports_count(self, api_gateway_url: str):
        """ Get the count of reports of a station. """
        station = "S160"
        url = f"{api_gateway_url}/reports/{station}/count"
        response = requests.get(url)

        assert response.status_code == 200
        assert response.json() == {"message": "Report Counts"}
