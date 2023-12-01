import argparse
import datetime
from decimal import Decimal
import random
from typing import Optional, TypedDict

import boto3
from botocore.exceptions import ClientError

from stations import STATIONS


class Report(TypedDict):
    station: str
    date: str
    battery: float
    panel: float


def create_report(
        station: str,
        date: datetime.datetime,
        battery: Optional[float] = None,
        panel: Optional[float] = None
) -> Report:
    if battery is None:
        battery = 100 + random.random() * 100
    if panel is None:
        panel = 100 + random.random() * 100
    return {
        "station": station,
        "date": date.isoformat(),
        "battery": battery,
        "panel": panel
    }


def generate_random_data(num_days: int) -> tuple[list[Report], list[Report]]:
    """ Generate random data for each station
    """
    reports = []
    last_reports = []

    end_date = datetime.date.today()
    end_date = datetime.datetime(year=end_date.year, month=end_date.month, day=end_date.day)
    time_delta = datetime.timedelta(days=num_days)
    start_date = end_date - time_delta

    n_samples = 2
    time_delta = datetime.timedelta(hours=24 / n_samples)

    stations = set(STATIONS)
    stations.remove("Tonalapa")
    stations.remove("Caracol")
    sorted_stations = sorted(list(stations))

    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += time_delta

    options = [True, False]
    weights = [0.8, 0.2]

    for station in sorted_stations:
        choices = random.choices(options, weights, k=len(dates))
        # All stations will report in the last date
        choices[-1] = True
        for ii in range(len(dates) - 1):
            if choices[ii]:
                reports.append(create_report(station, dates[ii]))

        report = create_report(station, dates[-1])
        reports.append(report)
        last_reports.append(report)

    # Tonalapa will have a voltage below 10
    for ii in range(len(dates) - 1):
        reports.append(create_report("Tonalapa", dates[ii]))

    battery = 5.
    panel = 100 + random.random() * 100
    report = create_report("Tonalapa", dates[-1], battery, panel)

    reports.append(report)
    last_reports.append(report)

    for ii in range(len(dates) - 3):
        reports.append(create_report("Caracol", dates[ii]))

    report = create_report("Caracol", dates[-2])
    reports.append(report)
    last_reports.append(report)

    return reports, last_reports


def create_reports_table(ddb_resource, table_name: str):
    if "last" not in table_name.lower():
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
    else:
        return ddb_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": "station",
                    "KeyType": "HASH"
                },
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "station",
                    "AttributeType": "S"
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )


def create_table_if_not_exist(
        ddb_resource,
        table_name: str,
        endpoint_url: str
):
    """ Create a DynamoDB table if it does not exist.
    """
    table = ddb_resource.Table(table_name)
    try:
        table.item_count
    except ClientError as err:
        err_name = err.response["Error"]["Code"]
        if err_name == "ResourceNotFoundException" and "localhost" in endpoint_url:
            return create_reports_table(ddb_resource, table_name)
        else:
            raise ValueError("An error occurred with DynamoDB table")

    return table


def get_tables(endpoint_url: Optional[str]):
    if endpoint_url is None:
        ddb_resource = boto3.resource("dynamodb")
        reports_table = ddb_resource.Table("voltage-dev-ReportsTable-YFR5XT9RWVJQ")
        last_reports_table = ddb_resource.Table("voltage-dev-LastReportsTable-H1EEWTXUI42")
    else:
        ddb_resource = boto3.resource("dynamodb", endpoint_url=endpoint_url)
        reports_table = create_table_if_not_exist(
            ddb_resource, "VoltageReportsTableLocal", endpoint_url
        )
        last_reports_table = create_table_if_not_exist(
            ddb_resource, "VoltageLastReportsLocal", endpoint_url
        )
    return reports_table, last_reports_table


def add_data_to_dynamo(table, reports: list[Report]) -> None:
    batch_chunks = [reports[i:i + 25] for i in range(0, len(reports), 25)]
    for chunk in batch_chunks:
        with table.batch_writer() as batch:
            for item in chunk:
                battery = Decimal(str(item["battery"]))
                panel = Decimal(str(item["panel"]))
                batch.put_item(Item={
                    "station": item["station"],
                    "date": item["date"],
                    "battery": battery,
                    "panel": panel,
                })


def clear_reports_table(table) -> None:
    response = table.scan()
    with table.batch_writer() as batch:
        for item in response["Items"]:
            batch.delete_item(Key={
                "station": item["station"],
                "date": item["date"]
            })


def clear_last_reports_table(table) -> None:
    response = table.scan()
    with table.batch_writer() as batch:
        for item in response["Items"]:
            batch.delete_item(
                Key={"station": item["station"]}
            )


def add_dynamo_endpoint_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
    "--endpoint-url",
        "-e",
        required=False,
        type=str,
        help="The endpoint URL for DynamoDB"
    )


def create_add_parser(
        subparsers,
        name: str,
        description: str
) -> argparse.ArgumentParser:
    new_parser = subparsers.add_parser(name, help=description)
    if "last" not in name:
        new_parser.add_argument(
            "--days",
            "-d",
            type=int,
            default=15,
            help="Number of days to generate reports data. "
                 "The first report will have date from today minus the days"
                 "specified here. (default 15)"
        )
    add_dynamo_endpoint_argument(new_parser)
    return new_parser


def create_remove_parser(
        subparsers,
        name: str,
        description: str
) -> argparse.ArgumentParser:
    new_parser = subparsers.add_parser(name, help=description)
    add_dynamo_endpoint_argument(new_parser)
    return new_parser


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose whether to add data or remove data from the DynamoDB tables"
    )

    create_add_parser(
        subparsers,
        "add",
        "Add reports to DynamoDB last reports and reports tables."
    )
    create_add_parser(
        subparsers,
        "add-last",
        "Add data to DynamoDB last report tables."
    )
    create_add_parser(
        subparsers,
        "add-reports",
        "Add data to DynamoDB reports tables."
    )

    create_remove_parser(
        subparsers,
        "remove",
        "Remove all data from the DynamoDB reports and last reports tables."
    )
    create_remove_parser(
        subparsers,
        "remove-last",
        "Remove all data from the DynamoDB last reports tables."
    )
    create_remove_parser(
        subparsers,
        "remove-reports",
        "Remove all data from the DynamoDB reports tables."
    )

    args = parser.parse_args()
    add_commands = ["add", "add-last", "add-reports"]
    remove_commands = ["remove", "remove-last", "remove-reports"]

    all_commands = add_commands + remove_commands
    if args.command not in all_commands:
        raise ValueError(f"Invalid command. Please choose between {all_commands}")

    endpoint_url: Optional[str] = args.endpoint_url
    reports_table, last_reports_table = get_tables(endpoint_url)

    if args.command in ["add", "add-last", "add-reports"]:
        days = 5
        try:
            days = args.days
        except AttributeError:
            pass

        reports, last_reports = generate_random_data(days)

        if args.command == "add-reports" or args.command == "add":
            print(f"Generated {len(reports)} reports")
            print("Adding data to reports table...")
            add_data_to_dynamo(reports_table, reports)

        if args.command == "add-last" or args.command == "add":
            print(f"Generated {len(last_reports)} last reports")
            print("Adding data to last reports table...")
            add_data_to_dynamo(last_reports_table, last_reports)

    else:

        if args.command == "remove-reports" or args.command == "remove":
            print("Clearing reports table...")
            clear_reports_table(reports_table)

        if args.command == "remove-last" or args.command == "remove":
            print("Clearing last reports table...")
            clear_last_reports_table(last_reports_table)

    print("DONE")


if __name__ == "__main__":
    main()
