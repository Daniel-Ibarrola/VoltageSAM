import json


def lambda_handler(event, context):
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
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "List Last Reports",
        }),
    }
