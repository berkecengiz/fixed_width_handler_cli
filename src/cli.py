"""Command-line interface (CLI) for managing fixed-width files."""

import argparse
import logging

from src.core import FixedWidthFile

# Setup logging
logger = logging.getLogger("cli")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_value(filename, field_name):
    """
    Retrieve the value of a field from a fixed-width file.

    Args:
        filename (str): Path to the fixed-width file.
        field_name (str): Name of the field to retrieve.

    Returns:
        str: The value of the field if found, None otherwise.
    """
    try:
        fixed_width_file = FixedWidthFile(filename)
        fixed_width_file.read()
        for records in fixed_width_file.data.values():
            for record in records:
                if field_name in record:
                    return record[field_name]
        logger.info("Field '%s' not found in file '%s'.", field_name, filename)
    except FileNotFoundError:
        logger.error("File not found: %s", filename)
    except IOError as e:
        logger.error("I/O error occurred while reading the file '%s': %s", filename, e)
    except ValueError as e:
        logger.error("Value error occurred: %s", e)
    return None


def set_value(filename, field_name, value):
    """
    Set the value of a field in a fixed-width file.

    Args:
        filename (str): Path to the fixed-width file.
        field_name (str): Name of the field to set.
        value (str): New value for the field.

    Returns:
        bool: True if the field was successfully updated, False otherwise.
    """
    try:
        fixed_width_file = FixedWidthFile(filename)
        fixed_width_file.read()
        updated = False
        for records in fixed_width_file.data.values():
            for record in records:
                if field_name in record:
                    record[field_name] = value
                    updated = True
        if updated:
            fixed_width_file.write()
            logger.info(
                "Successfully updated field '%s' to '%s' in file '%s'.",
                field_name,
                value,
                filename,
            )
            return True
        logger.info("Field '%s' not found in file '%s'.", field_name, filename)
    except FileNotFoundError:
        logger.error("File not found: %s", filename)
    except IOError as e:
        logger.error("I/O error occurred while writing to file '%s': %s", filename, e)
    except ValueError as e:
        logger.error("Value error occurred while updating the file: %s", e)
    return False


def add_transaction(filename, amount, currency):
    """
    Add a new transaction to a fixed-width file.

    Args:
        filename (str): Path to the fixed-width file.
        amount (str): Amount of the transaction.
        currency (str): Currency code for the transaction.

    Returns:
        bool: True if the transaction was successfully added, False otherwise.
    """
    try:
        fixed_width_file = FixedWidthFile(filename)
        fixed_width_file.read()
        # Automatically generate the next counter
        counter = str(len(fixed_width_file.data.get("TRANSACTION", [])) + 1).zfill(6)
        new_transaction = {
            "field_id": "02",
            "counter": counter,
            "amount": f"{amount:.2f}",  # Format amount as a fixed-point number with two decimals
            "currency": currency,
        }
        fixed_width_file.data.setdefault("TRANSACTION", []).append(new_transaction)
        fixed_width_file.write()
        logger.info("Added new transaction to file '%s'.", filename)
        return True
    except FileNotFoundError:
        logger.error("File not found: %s", filename)
    except IOError as e:
        logger.error("I/O error occurred: %s", e)
    except ValueError as e:
        logger.error("Value error during transaction addition: %s", e)
    return False


def main():
    """
    The main entry point of the CLI application.
    """
    parser = argparse.ArgumentParser(
        description="Manage and manipulate fixed-width files."
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands available")

    # get command
    get_parser = subparsers.add_parser(
        "get", help="Retrieve a field value from the file"
    )
    get_parser.add_argument("filename", help="Path to the fixed-width file")
    get_parser.add_argument("field_name", help="Name of the field to retrieve")

    # set command
    set_parser = subparsers.add_parser(
        "set", help="Set a new value for a field in the file"
    )
    set_parser.add_argument("filename", help="Path to the fixed-width file")
    set_parser.add_argument("field_name", help="Name of the field to set")
    set_parser.add_argument("value", help="New value for the field")

    # add command
    add_parser = subparsers.add_parser("add", help="Add a new transaction to the file")
    add_parser.add_argument("filename", help="Path to the fixed-width file")
    add_parser.add_argument(
        "amount", type=float, help="Amount of the transaction (format: 1234.56)"
    )
    add_parser.add_argument(
        "currency", help="Currency code for the transaction (e.g., USD, EUR, GBP)"
    )

    args = parser.parse_args()

    if args.command == "get":
        value = get_value(args.filename, args.field_name)
        if value is not None:
            print(f"Value of '{args.field_name}': {value}")
        else:
            print("Failed to retrieve value.")
    elif args.command == "set":
        if set_value(args.filename, args.field_name, args.value):
            print(f"Successfully set '{args.field_name}' to '{args.value}'.")
        else:
            print("Failed to set value.")
    elif args.command == "add":
        if add_transaction(args.filename, args.amount, args.currency):
            print("Successfully added a new transaction.")
        else:
            print("Failed to add transaction.")
    else:
        print("Unknown command.")
