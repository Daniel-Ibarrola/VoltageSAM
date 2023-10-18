import json

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.list_reports.schema import OUTPUT_SCHEMA


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
