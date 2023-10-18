OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "title": "List Reports Lambda Output Schema",
    "description": "Output for listing the reports of a station",
    "properties": {
        "statusCode": {
            "type": "integer",
            "description": "HTTP Status Code",
            "examples": [200, 401, 500]
        },
        "body": {
            "type": "string",
            "description": "Array with the reports of a station encoded as a json string",
            "examples": [
                '{"date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0}'
                '{"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},'
            ],
        }
    },
    "required": ["statusCode", "body"],
}
