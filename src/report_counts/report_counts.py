import datetime
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
    from src.report_counts.schema import OUTPUT_SCHEMA


def get_dynamodb_resource(t_name: str):
    t_name = t_name.lower()
    if "local" in t_name:
        return boto3.resource('dynamodb', endpoint_url="http://dynamo-local:8000")
    else:
        return boto3.resource('dynamodb')


table_name = os.environ["REPORTS_TABLE"]
dynamodb_resource = get_dynamodb_resource(table_name)


def respond(status_code: int, body: list | dict | str) -> dict:
    """ A response in the format that API Gateway expects.
    """
    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }


@validator(outbound_schema=OUTPUT_SCHEMA)
def lambda_handler(event: APIGatewayProxyEvent, context: LambdaContext) -> dict:
    """ Get the number of reports per date of a given station

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict
    """
    table = dynamodb_resource.Table(table_name)
    path_params = event.get("pathParameters")
    station = ""
    if path_params is not None:
        station: str = path_params.get("station", "")

    if not path_params or not station:
        print("Failed to get station path parameter")
        return respond(400, {"message": "Need to pass a station"})

    print(f"Requested report counts for station {station}")
    ddb_response = table.query(
        KeyConditionExpression=Key("station").eq(station.lower()),
        ScanIndexForward=False
    )
    reports = ddb_response["Items"]
    if not reports:
        print(f"Did not find reports for station {station}")
        return respond(404, {"message": f"Station '{station}' not found"})

    print("Reports", reports)
    counts = {}
    for rep in reports:
        date = datetime.datetime.fromisoformat(rep["date"]).date()
        date_str = date.isoformat()
        counts[date_str] = counts.get(date_str, 0) + 1

    response = []
    for date, cnt in counts.items():
        response.append({"count": cnt, "date": date})

    return respond(200, {"reports": response})
