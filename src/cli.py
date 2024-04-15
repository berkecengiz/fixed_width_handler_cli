"""Command-line interface (CLI) for managing fixed-width files."""

import argparse
import logging

from src.fixed_width_file import FixedWidthFile

logger = logging.getLogger("cli")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def add_transaction(filename, amount, currency):
    """
    Adds a new transaction to the specified fixed-width file.

    Args:
        filename (str): Path to the fixed-width file.
        amount (float): Amount of the transaction.
        currency (str): Currency code for the transaction.
    """
    fixed_width_file = FixedWidthFile(filename)
    if fixed_width_file.add_transaction(amount, currency):
        return "Successfully added a new transaction."
    return "Failed to add transaction."


def get_value(filename, record_type, field_name, transaction_counter=None):
    """
    Retrieve the value of a field from a fixed-width file for a specific record type.

    Args:
        filename (str): Path to the fixed-width file.
        record_type (str): The type of record (e.g., HEADER, TRANSACTION, FOOTER).
        field_name (str): Name of the field to retrieve.
        transaction_counter (str, optional): Counter of the transaction to retrieve.

    Returns:
        str or None: The value of the field if found, or None if not found.
    """
    try:
        fixed_width_file = FixedWidthFile(filename)
        records = fixed_width_file.read()
        if records:
            filtered_records = [
                record
                for record in records
                if record["type"] == record_type.upper()
                and (
                    not transaction_counter
                    or record.get("counter") == transaction_counter
                )
            ]
            for record in filtered_records:
                if field_name in record:
                    return str(record[field_name])
            logger.info(
                "No '%s' records or transactions with counter '%s' in '%s'.",
                record_type,
                transaction_counter,
                filename,
            )
    except FileNotFoundError:
        logger.error("File not found: %s", filename)
    except IOError as e:
        logger.error("I/O error occurred while reading the file '%s': %s", filename, e)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error: %s", e)
    return None


def set_value(filename, record_type, field_name, value, transaction_counter=None):
    """
    Sets a new value for a field in a specified fixed-width file.
    """
    fixed_width_file = FixedWidthFile(filename)
    if fixed_width_file.set_value(record_type, field_name, value, transaction_counter):
        return f"Successfully set '{field_name}' to '{value}'."

    return "Failed to set value."


def main():
    """
    The main entry point of the CLI application.
    """
    parser = argparse.ArgumentParser(
        description="Manage and manipulate fixed-width files."
    )
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers(dest="command", help="Commands available")

    # get command
    get_parser = subparsers.add_parser(
        "get",
        help="Retrieve a field value from the file. Example: get filename HEADER field_name",
    )
    get_parser.add_argument("filename", help="Path to the fixed-width file")
    get_parser.add_argument(
        "record_type",
        help="The type of record to retrieve from",
        choices=["HEADER", "TRANSACTION", "FOOTER"],
    )
    get_parser.add_argument("field_name", help="Name of the field to retrieve")
    get_parser.add_argument(
        "--transaction_counter",
        help="Transaction counter for filtering",
        required=False,
    )
    get_parser.set_defaults(func=get_value)

    # set command
    set_parser = subparsers.add_parser(
        "set",
        help="Set a new value for a field in the file. Example: set filename field_name value",
    )
    set_parser.add_argument("filename", help="Path to the fixed-width file")
    set_parser.add_argument(
        "record_type",
        help="The type of record to set the field in",
        choices=["HEADER", "TRANSACTION", "FOOTER"],
    )
    set_parser.add_argument("field_name", help="Name of the field to set")
    set_parser.add_argument("value", help="New value for the field")
    set_parser.add_argument(
        "--transaction_counter",
        help="Transaction counter for filtering",
        required=False,
    )
    set_parser.set_defaults(func=set_value)

    # add command
    add_parser = subparsers.add_parser(
        "add",
        help="Add a new transaction to the file. Example: add filename amount currency",
    )
    add_parser.add_argument("filename", help="Path to the fixed-width file")
    add_parser.add_argument(
        "amount", type=float, help="Amount of the transaction (format: 1234.56)"
    )
    add_parser.add_argument(
        "currency", help="Currency code for the transaction (e.g., USD, EUR, GBP)"
    )
    add_parser.set_defaults(func=add_transaction)

    args = parser.parse_args()

    if args.command == "get":
        value = get_value(
            args.filename, args.record_type, args.field_name, args.transaction_counter
        )
        if value is not None:
            print(f"Value of '{args.field_name}': {value}")
        else:
            print("Failed to retrieve value.")
    elif args.command == "set":
        if set_value(
            args.filename,
            args.record_type,
            args.field_name,
            args.value,
            args.transaction_counter,
        ):
            print(f"Successfully set '{args.field_name}' to '{args.value}'.")
        else:
            print("Failed to set value.")
    elif args.command == "add":
        if add_transaction(args.filename, args.amount, args.currency):
            print("Successfully added a new transaction.")
        else:
            print("Failed to add transaction.")
    else:
        parser.print_help()
