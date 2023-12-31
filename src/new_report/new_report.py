from datetime import datetime
from decimal import Decimal
import os
import json
from urllib.parse import unquote

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator
import boto3

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.new_report.schema import OUTPUT_SCHEMA


def get_dynamodb_resource(t_name: str):
    t_name = t_name.lower()
    if "local" in t_name:
        return boto3.resource('dynamodb', endpoint_url="http://dynamo-local:8000")
    else:
        return boto3.resource('dynamodb')


reports_tb_name = os.environ["REPORTS_TABLE"]
last_reports_tb_name = os.environ["LAST_REPORTS_TABLE"]
dynamodb_resource = get_dynamodb_resource(reports_tb_name)


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
    """ Add a new report

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
    reports_tb = dynamodb_resource.Table(reports_tb_name)
    last_reports_tb = dynamodb_resource.Table(last_reports_tb_name)

    body_str = event.get("body", "")
    if not body_str:
        print("Failed to add new report. Event did not contain body")
        return respond(
            400, {"message": "Need to pass the body with the new report parameters"})

    body: dict = json.loads(body_str)
    if "station" not in body or "date" not in body \
            or "panel" not in body or "battery" not in body:
        print(f"Failed to add new report. Incomplete event body {body}")
        return respond(
            400,
            {"message": "The new report must include station, date, report and panel attributes"},
            cors_origin
        )

    date = datetime.strptime(body["date"], "%Y/%m/%d,%H:%M:%S").isoformat()
    station = body["station"]
    station = unquote(station)
    battery = Decimal(body["battery"])
    panel = Decimal(body["panel"])

    reports_tb.put_item(
        Item={
            "station": station,
            "date": date,
            "battery": battery,
            "panel": panel
        }
    )
    last_reports_tb.update_item(
        Key={"station": station},
        UpdateExpression="SET #date=:newDate, #battery =:newBattery, #panel =:newPanel",
        ExpressionAttributeValues={
            ":newDate": date,
            ":newBattery": battery,
            ":newPanel": panel
        },
        ExpressionAttributeNames={
            "#date": "date",
            "#battery": "battery",
            "#panel": "panel"
        }
    )
    res_body = {
        "station": station,
        "date": date,
        "battery": body["battery"],
        "panel": body["panel"]
    }
    return respond(201, res_body, cors_origin)
