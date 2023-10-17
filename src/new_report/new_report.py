import json


def lambda_handler(event, context):
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
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
        }),
    }
