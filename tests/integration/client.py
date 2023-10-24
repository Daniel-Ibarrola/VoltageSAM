import os
import pickle
from typing import Literal, Optional
import time

import boto3
import requests

from tests.integration.env import get_env_var


class APIClient:
    """ Client that consumes the Voltage REST API"""

    def __init__(self, api_host: Literal["aws", "localhost"]):
        self.api_host = api_host
        self.api_gateway_url = self.get_api_gateway_url()
        self.auth_token, self.expiration = self.get_auth_token()

    def get_api_gateway_url(self) -> str:
        """ Get the API URL. The API can be running locally or on AWS
        """
        if self.api_host == "localhost":
            return "http://localhost:3000"
        else:
            api_id = get_env_var("API_GATEWAY_ID")
            region = "us-east-2"
            return f"https://{api_id}.execute-api.{region}.amazonaws.com/Prod"

    def get_auth_token(self) -> tuple[str, Optional[int]]:
        """ Get a token to authenticate to API Gateway. """
        if self.api_host == "aws":

            if os.path.exists("token.pickle"):
                # TODO: make token path absolute
                with open("token.pickle", "rb") as fp:
                    token, expiration = pickle.load(fp)

                if expiration < time.time() - 5:
                    print("Loading token from file")
                    return token, expiration

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

            with open("token.pickle", "wb") as fp:
                pickle.dump((id_token, expiration), fp)
                print("Saved token to file")

            return id_token, expiration

        else:
            return "", None

    def new_station_report(self, station: str, date: str, battery: float, panel: float) -> requests.Response:
        url = f"{self.api_gateway_url}/reports"

        if not self.auth_token:
            return requests.post(url, json={
                "station": station,
                "date": date,
                "battery": battery,
                "panel": panel,
            })

        if self.expiration >= time.time() - 10:
            self.auth_token, self.expiration = self.get_auth_token()

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

        if self.expiration >= time.time() - 10:
            self.auth_token, self.expiration = self.get_auth_token()

        headers = {"Authorization": self.auth_token}
        return requests.get(url, headers=headers)

    def station_reports(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/reports/{station}"
        response = requests.get(url)
        return response

    def station_last_report(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/last_reports/{station}"
        response = requests.get(url)
        return response

    def last_reports(self) -> requests.Response:
        url = f"{self.api_gateway_url}/last_reports"
        response = requests.get(url)
        return response

    def station_reports_count(self, station: str) -> requests.Response:
        url = f"{self.api_gateway_url}/reports/{station}/count"
        response = requests.get(url)
        return response
