OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "title": "Report Counts Lambda Output Schema",
    "description": "The number of reports per day of a station",
    "properties": {
        "statusCode": {
            "type": "integer",
            "description": "HTTP Status Code",
            "examples": [200, 401, 500]
        },
        "body": {
            "type": "string",
            "description": "Number of reports per day as a json encoded string",
            "examples": [
                '{"date": "2023-02-22", "count": 1}'
                '{"date": "2023-02-23", "count": 1}'
            ],
        }
    },
    "required": ["statusCode", "body"],
}
