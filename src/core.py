"""
Core module for handling fixed-width files.
Provides the FixedWidthFile class for handling fixed-width file operations.
"""

import decimal
import logging
import os
import re

logger = logging.getLogger("FixedWidthFile")
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class FixedWidthFile:
    """
    Handles reading, parsing, validating, and writing fixed-width file formats.
    """
    RECORD_LENGTH = 120
    FIELD_DEFINITIONS = {
        "HEADER": {
            "field_id": (0, 2),
            "name": (2, 30),
            "surname": (30, 60), # From position 31 to 60, inclusively
            "patronymic": (60, 90), # From position 61 to 90, inclusively
            "address": (90, 120),   # From position 91 to 120, inclusively
        },
        "TRANSACTION": {
            "field_id": (0, 2),  # From position 1 to 2, inclusively
            "counter": (2, 8),   # From position 3 to 8, inclusively
            "amount": (8, 20),   # From position 9 to 20, inclusively
            "currency": (20, 23), # From position 21 to 23, inclusively
            "reserved": (23, 120), # From position 24 to 120, inclusively
        },
        "FOOTER": {
            "field_id": (0, 2),    # From position 1 to 2, inclusively
            "total_count": (2, 8), # From position 3 to 8, inclusively
            "control_sum": (8, 20), # From position 9 to 20, inclusively
            "reserved": (20, 120), # From position 21 to 120, inclusively
        },
    }

    def __init__(self, filename):
        """
        Initialize the FixedWidthFile object with a file name.
        """
        self.filename = filename
        self.data = {}
        self.transaction_counter = 0  # To handle transaction counters automatically
        logger.debug("FixedWidthFile initialized for file: %s", filename)

    def _get_record_type(self, line):
        """
        Identify the type of record based on its field ID.
        """
        field_id = line[:2]
        if field_id == "01":
            return "HEADER"
        if field_id == "02":
            return "TRANSACTION"
        if field_id == "03":
            return "FOOTER"
        logger.error("Invalid record type ID: %s", field_id)
        raise ValueError(f"Invalid record type ID: {field_id}")

    def _parse_line(self, line, record_type):
        """
        Parse a line based on the record type and extract field data.
        """
        data = {}
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = line[start:end].strip()
            if record_type == "TRANSACTION":
                if field_name == "amount":
                    try:
                        amount_decimal = decimal.Decimal(value[:-2] + "." + value[-2:])
                        data[field_name] = amount_decimal
                    except decimal.InvalidOperation:
                        logger.error(f"Invalid amount format: '{value}' in line: '{line}'")
                        raise ValueError(f"Invalid amount format: '{value}'")
                elif field_name == "currency":
                    allowed_currencies = ["USD", "EUR", "GBP"]
                    if value not in allowed_currencies:
                        logger.error(f"Invalid currency code: '{value}' in line: '{line}'")
                        raise ValueError(f"Invalid currency code: '{value}'")
                    data[field_name] = value
                else:
                    data[field_name] = value
            else:
                data[field_name] = value
        if record_type == "TRANSACTION":
            # Automatic increment of the transaction counter
            self.transaction_counter += 1
            data["counter"] = f"{self.transaction_counter:06}"  # Format as a zero-padded string
        logger.debug(f"Parsed data for {record_type}: {data}")
        return data

    def _validate_data(self, data, record_type):
        """
        Validate parsed data based on the record type.
        """
        if record_type == "TRANSACTION":
            allowed_currencies = ["USD", "EUR", "GBP"]
            if data["currency"] not in allowed_currencies:
                logger.error("Invalid currency code: %s", data["currency"])
                raise ValueError(f"Invalid currency code: {data['currency']}")

    def read(self):
        """
        Read and process the fixed-width file, handling newline characters.
        """
        logger.info("Reading file: %s", self.filename)
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    clean_line = line.rstrip().replace("\\n", "\n")
                    if len(clean_line) == self.RECORD_LENGTH:
                        record_type = self._get_record_type(clean_line)
                        data = self._parse_line(clean_line, record_type)
                        self._validate_data(data, record_type)
                        self.data.setdefault(record_type, []).append(data)
                    else:
                        logger.error("Invalid line length: %d at line %d", len(clean_line), line_number)
                        raise ValueError(f"Invalid line length: {len(clean_line)} at line {line_number}")
            logger.info("File read successfully")
        except FileNotFoundError:
            logger.error("File not found: %s", self.filename)
            raise
        except Exception as e:
            logger.error("An error occurred while reading the file: %s", e)
            raise

    def write(self):
        """
        Write processed data back to a fixed-width file format.
        """
        logger.info("Writing data to file: %s", self.filename)
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                for record_type, records in self.data.items():
                    for data in records:
                        line = self._format_line(data, record_type)
                        f.write(line + os.linesep)
            logger.info("Data written successfully")
        except Exception as e:
            logger.error("Failed to write to file: %s", e)
            raise

    def _format_line(self, data, record_type):
        """
        Formats a line of data based on the record type.

        Args:
            data (dict): A dictionary containing the data to format.
            record_type (str): The type of the record ("HEADER", "TRANSACTION", "FOOTER").

        Returns:
            str: The formatted line.
        """
        line = ""

        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = str(data.get(field_name, ""))
            # Ensure value does not exceed its defined space
            formatted_value = value.ljust(end - start + 1)[: end - start + 1]
            line += formatted_value
        return line
