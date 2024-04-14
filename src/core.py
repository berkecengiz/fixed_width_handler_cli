"""
Core module for handling fixed-width files.
Provides the FixedWidthFile class for handling fixed-width file operations.
"""

import decimal
import logging
import os

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
            "field_id": (1, 2),
            "name": (3, 30),
            "surname": (31, 60),
            "patronymic": (61, 90),
            "address": (91, 120),
        },
        "TRANSACTION": {
            "field_id": (1, 2),
            "counter": (3, 8),
            "amount": (9, 20),
            "currency": (21, 23),
            "reserved": (24, 120),
        },
        "FOOTER": {
            "field_id": (1, 2),
            "total_count": (3, 8),
            "control_sum": (9, 20),
        },
    }

    def __init__(self, filename):
        """
        Initialize the FixedWidthFile object with a file name.
        """
        self.filename = filename
        self.data = {}
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
            value = line[start - 1 : end].strip()
            if record_type == "TRANSACTION" and field_name == "amount":
                # Convert string amount to decimal assuming last two digits are decimal part
                data[field_name] = decimal.Decimal(value[:-2] + "." + value[-2:])
            else:
                data[field_name] = value
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
        Read and process the fixed-width file.
        """
        logger.info("Reading file: %s", self.filename)
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                for line in f:
                    if len(line.rstrip()) != self.RECORD_LENGTH:
                        logger.error("Invalid line length: %s", len(line.strip()))
                        raise ValueError(f"Invalid line length: {len(line.strip())}")
                    record_type = self._get_record_type(line)
                    data = self._parse_line(line, record_type)
                    self._validate_data(data, record_type)
                    self.data.setdefault(record_type, []).append(data)
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
