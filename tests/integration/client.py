from datetime import datetime
import os
import pickle
from typing import Literal
import time

import boto3
import requests

from tests.integration.env import get_env_var


class APIClient:
    """ Client that consumes the Voltage REST API"""

    def __init__(self, api_host: Literal["aws", "localhost"]):
        self.api_host = api_host
        self.api_gateway_url = self.get_api_gateway_url()
        self.token_file_path = self.get_token_file_path()
        self.auth_token = ""
        self.expiration = None

    @staticmethod
    def get_token_file_path() -> str:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(this_dir, "token.pickle")

    def get_api_gateway_url(self) -> str:
        """ Get the API URL. The API can be running locally or on AWS
        """
        if self.api_host == "localhost":
            return "http://localhost:3000"
        else:
            api_id = get_env_var("API_GATEWAY_ID")
            region = "us-east-2"
            return f"https://{api_id}.execute-api.{region}.amazonaws.com/Prod"

    def get_auth_token(self):
        """ Get a token to authenticate to API Gateway. """
        if self.api_host == "aws":
            if os.path.exists(self.token_file_path):
                with open(self.token_file_path, "rb") as fp:
                    token, expiration = pickle.load(fp)
                    print(f"Found token file. Expiration is {datetime.fromtimestamp(expiration)}")

                if expiration > time.time():
                    self.auth_token = token
                    self.expiration = expiration
                    return

            user = get_env_var("COGNITO_USER")
            password = get_env_var("COGNITO_PASSWORD")
            client_id = get_env_var("COGNITO_CLIENT_ID")

            client = boto3.client("cognito-idp")
            response = client.initiate_auth(
                AuthParameters={
                    "USERNAME": user,
                    "PASSWORD": password,
                },
                AuthFlow='USER_PASSWORD_AUTH',
                ClientId=client_id,
            )

            try:
                id_token = response["AuthenticationResult"]["IdToken"]
                expiration = response["AuthenticationResult"]["ExpiresIn"]  # in seconds
            except KeyError:
                raise ValueError("Failed to get authentication token")

            print("Successfully authenticated with Cognito")
            expiration = time.time() + expiration

            with open(self.token_file_path, "wb") as fp:
                pickle.dump((id_token, expiration), fp)
                print("Saved token to file")

            self.auth_token = id_token
            self.expiration = expiration

    def new_station_report(self, station: str, date: str, battery: float, panel: float) -> requests.Response:
        url = f"{self.api_gateway_url}/reports"

        if not self.auth_token:
            return requests.post(url, json={
                "station": station,
                "date": date,
                "battery": battery,
                "panel": panel,
            })

        headers = {"Authorization": self.auth_token}
        return requests.post(
            url,
            json={
                "station": station,
                "date": date,
                "battery": battery,
                "panel": panel,
            },
            headers=headers
        )

    def _get_request(self, url: str) -> requests.Response:
        if not self.auth_token:
            return requests.get(url)

        headers = {"Authorization": self.auth_token}
        return requests.get(url, headers=headers)

    def station_reports(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/reports/{station}"
        response = self._get_request(url)
        return response

    def station_last_report(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/last_reports/{station}"
        response = self._get_request(url)
        return response

    def last_reports(self) -> requests.Response:
        url = f"{self.api_gateway_url}/last_reports"
        response = self._get_request(url)
        return response

    def station_reports_count(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/reports/{station}/count"
        response = self._get_request(url)
        return response
