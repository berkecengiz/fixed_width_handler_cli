""" This module contains the RecordParser class. """

import logging

logger = logging.getLogger("FixedWidthFile")
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

class RecordParser:
    """
    Parses and formats records for fixed-width files.
    """

    FIELD_DEFINITIONS = {
        "HEADER": {
            "field_id": (0, 2),
            "name": (2, 30),
            "surname": (30, 60),
            "patronymic": (60, 90),
            "address": (90, 118),
        },
        "TRANSACTION": {
            "field_id": (0, 2),
            "counter": (2, 8),
            "amount": (8, 20),
            "currency": (20, 23),
            "reserved": (23, 118),
        },
        "FOOTER": {
            "field_id": (0, 2),
            "total_count": (2, 8),
            "control_sum": (8, 20),
            "reserved": (20, 118),
        },
    }
    RECORD_LENGTH = 120
    ALLOWED_CURRENCIES = ["USD", "EUR", "GBP"]

    def get_record_type(self, line):
        """Get the record type based on the field ID.

        The field ID is the first two characters of the line.

        Args:
            line (str): The line to parse.

        Returns:
            str: The record type.
        """
        field_id = line[:2]
        record_types = {"01": "HEADER", "02": "TRANSACTION", "03": "FOOTER"}
        if field_id in record_types:
            return record_types[field_id]
        logger.error("Invalid record type ID: %s", field_id)
        raise ValueError(f"Invalid record type ID: {field_id}")

    def parse_line(self, line, record_type):
        """
        Parse a line into a dictionary based on the record type.

        Args:
            line (str): The line to parse.
            record_type (str): The record type.
        """
        data = {"type": record_type}
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            data[field_name] = line[start:end].strip()
        return data

    def format_line(self, data, record_type):
        """Format a line based on the record type.

        Args:
            data (dict): The data to format.
            record_type (str): The record type.

        Returns:
            str: The formatted line.
        """
        formatted_line = ""
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = data.get(field_name, "")
            field_length = end - start
            if field_name == "amount":
                formatted_value = value.zfill(field_length)
            else:
                formatted_value = value.ljust(field_length)
            formatted_line += formatted_value
        return formatted_line
