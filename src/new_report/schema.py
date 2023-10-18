OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "title": "Add New Report Lambda Output Schema",
    "description": "Add a new report to database.",
    "properties": {
        "statusCode": {
            "type": "integer",
            "description": "HTTP Status Code",
            "examples": [200, 401, 500]
        },
        "body": {
            "type": "string",
            "description": "The newly added report",
        }
    },
    "required": ["statusCode", "body"],
}
