from decimal import Decimal

TABLE_NAME = "test_table"


def fill_table(table, station: str) -> list[dict]:
    """ Fill the DynamoDB table for testing."""
    reports = [
        {"station": station, "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
        {"station": station, "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
        {"station": "Piedra Grande", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0}
    ]
    for rep in reports:
        table.put_item(Item={
            "station": rep["station"],
            "date": rep["date"],
            "battery": Decimal(rep["battery"]),
            "panel": Decimal(rep["panel"]),
        })

    return reports

