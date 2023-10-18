OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "title": "List Last Reports Lambda Output Schema",
    "description": "Output for the last reports of all stations",
    "properties": {
        "statusCode": {
            "type": "integer",
            "description": "HTTP Status Code",
            "examples": [200, 401, 500]
        },
        "body": {
            "type": "string",
            "description": "The list with last report encoded as a json string",
            "examples": [
                '{"station": "tonalapa", "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0}'
                '{"station": "piedra grande", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}'
            ]
        }
    },
    "required": ["statusCode", "body"],
}
