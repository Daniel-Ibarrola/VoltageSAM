import os
import json

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator
import boto3

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.list_last.schema import OUTPUT_SCHEMA


def get_dynamodb_resource(t_name: str):
    t_name = t_name.lower()
    if "local" in t_name:
        return boto3.resource('dynamodb', endpoint_url="http://dynamo-local:8000")
    else:
        return boto3.resource('dynamodb')


table_name = os.environ["LAST_REPORTS_TABLE"]
dynamodb_resource = get_dynamodb_resource(table_name)


def get_cors_origin(lambda_fn_name: str) -> str:
    if "prod" in lambda_fn_name:
        return "https://api.voltage.cires-ac.mx"
    else:
        return "*"


def respond(
        status_code: int, body: list | dict | str,
        cors_origin: str = "*"
) -> dict:
    """ A response in the format that API Gateway expects.
    """
    return {
        "statusCode": status_code,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': cors_origin,
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        "body": json.dumps(body)
    }


@validator(outbound_schema=OUTPUT_SCHEMA)
def lambda_handler(event: APIGatewayProxyEvent, context: LambdaContext) -> dict:
    """ Get the last reports of all stations

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
    dict
    """
    cors_origin = get_cors_origin(context.function_name)
    table = dynamodb_resource.Table(table_name)
    response = table.scan()
    reports = response["Items"]
    for rep in reports:
        rep["battery"] = float(rep["battery"])
        rep["panel"] = float(rep["panel"])
    print("Reports", reports)
    return respond(200, {"reports": reports}, cors_origin)
