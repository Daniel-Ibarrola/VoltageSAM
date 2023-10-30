from decimal import Decimal


def create_reports_table(ddb_resource, table_name: str):
    return ddb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {
                "AttributeName": "station",
                "KeyType": "HASH"
            },
            {
                "AttributeName": "date",
                "KeyType": "RANGE"
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": "station",
                "AttributeType": "S"
            },
            {
                "AttributeName": "date",
                "AttributeType": "S"
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def fill_tables(reports_table, last_reports_table, station: str) -> list[dict]:
    """ Fill the DynamoDB tables for testing."""
    reports = [
        {"station": station, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
        {"station": station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        {"station": "piedra grande", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0}
    ]
    for ii, rep in enumerate(reports):
        reports_table.put_item(Item={
            "station": rep["station"],
            "date": rep["date"],
            "battery": Decimal(rep["battery"]),
            "panel": Decimal(rep["panel"]),
        })
        if ii > 0:
            last_reports_table.put_item(Item={
                "station": rep["station"],
                "date": rep["date"],
                "battery": Decimal(rep["battery"]),
                "panel": Decimal(rep["panel"]),
            })

    return reports
