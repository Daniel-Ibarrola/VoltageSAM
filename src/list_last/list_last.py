import json

from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator

try:
    from schema import OUTPUT_SCHEMA
except ModuleNotFoundError:
    from src.list_last.schema import OUTPUT_SCHEMA


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
    # TODO: create last reports table
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "List Last Reports",
        }),
    }
