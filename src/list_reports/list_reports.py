import os
import json

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator
import boto3
from boto3.dynamodb.conditions import Key

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.list_reports.schema import OUTPUT_SCHEMA


def get_dynamodb_resource(t_name: str):
    t_name = t_name.lower()
    if "local" in t_name:
        return boto3.resource('dynamodb', endpoint_url="http://dynamo-local:8000")
    else:
        return boto3.resource('dynamodb')


table_name = os.environ["DYNAMODB_TABLE_NAME"]
dynamodb_resource = get_dynamodb_resource(table_name)
table = dynamodb_resource.Table(table_name)


def respond(status_code: int, body: list | dict | str) -> dict:
    """ A response in the format that API Gateway expects.
    """
    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }


@validator(outbound_schema=OUTPUT_SCHEMA)
def lambda_handler(event: APIGatewayProxyEvent, context: LambdaContext):
    """ Get the reports of a station

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
    path_params = event.get("pathParameters")
    station = ""
    if path_params is not None:
        station: str = path_params.get("station", "")

    if not path_params or not station:
        print("Failed to get station path parameter")
        return respond(400, {"message": "Need to pass a station"})

    print(f"Requested reports for station {station}")

    query_params = event.get("queryStringParameters")
    if query_params is not None:
        start_date = query_params.get("start_date", "")
    else:
        start_date = None

    if not start_date:
        ddb_res = table.query(KeyConditionExpression=Key("station").eq(station.lower()))
    else:
        ddb_res = table.query(
            KeyConditionExpression=Key("station").eq(station.lower()) & Key("date").gte(start_date)
        )

    reports = ddb_res["Items"]
    if not reports:
        print(f"Did not find reports for station {station}")
        return respond(404, {"message": f"Station '{station}' not found"})

    for rep in reports:
        rep["battery"] = float(rep["battery"])
        rep["panel"] = float(rep["panel"])

    return respond(200, reports)
