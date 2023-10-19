import os
import json

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator
import boto3

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.list_reports.schema import OUTPUT_SCHEMA


table_name = os.environ["DYNAMODB_TABLE_NAME"]
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(table_name)


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
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "List Station Reports",
        }),
    }
