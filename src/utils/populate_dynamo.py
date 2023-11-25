import argparse
from decimal import Decimal

import boto3

REPORTS = [
    {"station": "tonalapa", "date": "2023-02-22T16:20:00", "battery": 45.0, "panel": 68.0},
    {"station": "caracol", "date": "2023-02-23T16:20:00", "battery": 55.0, "panel": 60.0},
    {"station": "piedra grande", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0},
    {"station": "la piedra", "date": "2023-02-22T16:20:00", "battery": 34.0, "panel": 40.0},
]


def get_tables():
    ddb_resource = boto3.resource("dynamodb")
    reports_table = ddb_resource.Table("voltage-dev-ReportsTable-YFR5XT9RWVJQ")
    last_reports_table = ddb_resource.Table("voltage-dev-LastReportsTable-H1EEWTXUI42")
    return reports_table, last_reports_table


def add_data_to_dynamo(reports_table, last_reports_table) -> None:
    print("Adding data to reports and last reports table...")
    for rep in REPORTS:
        reports_table.put_item(Item={
            "station": rep["station"],
            "date": rep["date"],
            "battery": Decimal(rep["battery"]),
            "panel": Decimal(rep["panel"]),
        })
        last_reports_table.put_item(Item={
            "station": rep["station"],
            "date": rep["date"],
            "battery": Decimal(rep["battery"]),
            "panel": Decimal(rep["panel"]),
        })


def remove_data_from_dynamo(reports_table, last_reports_table) -> None:
    print("Removing data to reports and last reports table...")
    for rep in REPORTS:
        reports_table.delete_item(Key={
            "station": rep["station"],
            "date": rep["date"]
        })
        last_reports_table.delete_item(
            Key={"station": rep["station"]}
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose whether to add data or remove data from the DynamoDB tables"
    )
    subparsers.add_parser("add", help="Add data to the DynamoDB tables")
    subparsers.add_parser("remove", help="Remove data from the DynamoDB tables")

    args = parser.parse_args()
    if args.command not in ["add", "remove"]:
        raise ValueError("Invalid command. Please choose between 'add' or 'remove'")

    reports_table, last_reports_table = get_tables()
    if args.command == "add":
        add_data_to_dynamo(reports_table, last_reports_table)
    else:
        remove_data_from_dynamo(reports_table, last_reports_table)

    print("DONE")


if __name__ == "__main__":
    main()
