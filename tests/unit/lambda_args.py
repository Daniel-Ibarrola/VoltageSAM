import json
from typing import Optional


def generate_event(
        path_params: Optional[dict[str, str]] = None,
        query_string_params: Optional[dict[str, str]] = None,
        body: Optional[str | dict] = None
) -> dict:
    """ Generate an event for testing lambda functions.
    """
    if body is not None:
        body = json.dumps(body)

    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/path",
        "rawQueryString": "parameter1=value1&parameter1=value2&parameter2=value",
        "cookies": [
            "cookie1",
            "cookie2"
        ],
        "headers": {
            "Header1": "value1",
            "Header2": "value1,value2"
        },
        "queryStringParameters": query_string_params,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "authentication": {
                "clientCert": {
                    "clientCertPem": "CERT_CONTENT",
                    "subjectDN": "www.example.com",
                    "issuerDN": "Example issuer",
                    "serialNumber": "a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1",
                    "validity": {
                        "notBefore": "May 28 12:30:02 2019 GMT",
                        "notAfter": "Aug  5 09:36:04 2021 GMT"
                    }
                }
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "claim1": "value1",
                        "claim2": "value2"
                    },
                    "scopes": [
                        "scope1",
                        "scope2"
                    ]
                }
            },
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
                "method": "GET",
                "path": "/path",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.0.1/32",
                "userAgent": "agent"
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390
        },
        "body": body,
        "pathParameters": path_params,
        "isBase64Encoded": True,
        "stageVariables": {
            "stageVariable1": "value1",
            "stageVariable2": "value2"
        }
    }


class FakeLambdaContext:
    def __init__(
            self,
            function_name,
            function_version,
            invoked_function_arn,
            memory_limit_in_mb,
            aws_request_id,
            log_group_name,
            log_stream_name,
            identity=None,
            cognito_identity_id=None,
            cognito_identity_pool_id=None,
            client_context=None,
            custom=None,
            env=None,
    ):
        self.function_name = function_name
        self.function_version = function_version
        self.invoked_function_arn = invoked_function_arn
        self.memory_limit_in_mb = memory_limit_in_mb
        self.aws_request_id = aws_request_id
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name
        self.identity = identity
        self.cognito_identity_id = cognito_identity_id
        self.cognito_identity_pool_id = cognito_identity_pool_id
        self.client_context = client_context
        self.custom = custom
        self.env = env


def get_context() -> FakeLambdaContext:
    return FakeLambdaContext(
        function_name="TestLambdaFunction",
        function_version="1.0",
        invoked_function_arn="arn:aws:lambda:region:account-id:function:MyFunction",
        memory_limit_in_mb=256,
        aws_request_id="1234567890",
        log_group_name="/aws/lambda/MyFunction",
        log_stream_name="2023/11/28/[LATEST]abcdefgh1234567890",
        identity=None,
        cognito_identity_id=None,
        cognito_identity_pool_id=None,
        client_context=None,
        custom={"key1": "value1", "key2": "value2"},
        env={"AWS_EXECUTION_ENV": "AWS_Lambda_python3.8"},
    )
