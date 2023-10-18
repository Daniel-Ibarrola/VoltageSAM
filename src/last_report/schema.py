OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "title": "Last Report Lambda Output Schema",
    "description": "The root schema comprises the entire JSON document of the Return Schema.",
    "properties": {
        "statusCode": {
            "type": "integer",
            "description": "HTTP Status Code",
            "examples": [200, 401, 500]
        },
        "body": {
            "type": "string",
            "description": "The last report from the station. Contains date, battery and panel",
            "examples": ['{"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}'],
        }
    },
    "required": ["statusCode", "body"],
    "examples": [{"statusCode": 200, "body": '{"date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0}'}]
}
