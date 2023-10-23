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


table_name = os.environ["DYNAMODB_TABLE_NAME"]
dynamodb_resource = boto3.resource('dynamodb')
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
    try:
        station: str = event["pathParameters"]["station"]
    except KeyError:
        print("Failed to get station path parameter")
        return respond(400, {"message": "Need to pass a station"})

    print(f"Requested reports for station {station}")

    ddb_res = table.query(KeyConditionExpression=Key("station").eq(station.lower()))
    reports = ddb_res["Items"]
    if not reports:
        print(f"Did not find reports for station {station}")
        return respond(404, {"message": f"Station '{station}' not found"})

    for rep in reports:
        rep["battery"] = float(rep["battery"])
        rep["panel"] = float(rep["panel"])

    return respond(200, reports)
