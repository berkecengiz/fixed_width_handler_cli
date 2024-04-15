"""
Core module for handling fixed-width files.
Provides the FixedWidthFile class for handling fixed-width file operations.
"""

import decimal
import logging

from src.fixed_width_file_handler import FixedWidthFileManager
from src.record_parser import RecordParser

logger = logging.getLogger("FixedWidthFile")
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class FixedWidthFile:
    """Class for handling fixed-width files."""

    def __init__(self, filename):
        """Initialize the FixedWidthFile instance.

        Args:
            filename (str): The filename of the fixed-width file.
        """
        self.filename = filename
        self.file_manager = FixedWidthFileManager(filename)
        self.parser = RecordParser()
        self.transaction_counter = self.initialize_transaction_counter()

    def read(self):
        """Read the file and process the content.

        Returns:
            list: The processed records from the file.
        """
        lines = self.file_manager.read_lines()
        records = self.process_content(lines)
        return records

    def process_content(self, content):
        """Process the content of the file.

        Args:
            content (list): The content of the file as a list of lines.

        Raises:
            ValueError: If the line length is invalid.
        """
        processed_records = []
        for line in content:
            clean_line = line.strip()
            if len(clean_line) != self.parser.RECORD_LENGTH:
                logger.error("Invalid line length: %d", len(clean_line))
                raise ValueError("Invalid line length.")
            record_type = self.parser.get_record_type(clean_line)
            data = self.parser.parse_line(clean_line, record_type)
            self.validate_data(data, record_type)
            processed_records.append(data)
            self.transaction_counter += 1 if record_type == "TRANSACTION" else 0
        return processed_records

    def validate_data(self, data, record_type):
        """Validate the data based on the record type.

        Args:
            data (dict): The data to validate.
            record_type (str): The record type.
        """
        if (
            record_type == "TRANSACTION"
            and data["currency"] not in self.parser.ALLOWED_CURRENCIES
        ):
            logger.error("Invalid currency code: %s", data["currency"])
            raise ValueError(f"Invalid currency code: {data['currency']}")

    def add_transaction(self, amount, currency):
        """Add a transaction to the file.

        Args:
            amount (str): The transaction amount.
            currency (str): The currency code.

        Raises:
            ValueError: If the currency is invalid.
        """
        lines = self.file_manager.read_lines()
        new_transaction_data = {
            "field_id": "02",
            "counter": str(self.transaction_counter + 1).zfill(6),
            "amount": str(int(decimal.Decimal(amount) * 100)).zfill(12),
            "currency": currency,
            "reserved": " " * 95,
        }
        try:
            footer_index, _ = self.find_footer(lines)
        except ValueError:
            logger.error("Footer not found. Cannot add transaction.")
            return

        new_transaction_line = (
            self.parser.format_line(new_transaction_data, "TRANSACTION") + "\\n"
        )
        lines.insert(footer_index, new_transaction_line)
        self.update_footer(lines, self.transaction_counter + 1, decimal.Decimal(amount))
        self.file_manager.write_lines(lines)
        self.transaction_counter += 1

    def set_value(self, record_type, field_name, new_value, transaction_counter=None):
        """
        Set the value of a field in a specific record without needing to specify the record type.

        Args:
            field_name (str): The field to modify.
            new_value (str): The new value for the field.
            transaction_counter (str, optional): The counter of the transaction to update.

        Returns:
            bool: True if the field was successfully updated, False otherwise.
        """

        lines = self.file_manager.read_lines()
        updated = False
        for i, line in enumerate(lines):
            data = self.parser.parse_line(line, record_type)
            if self.matches_transaction_counter(data, transaction_counter):
                if field_name == "amount":
                    new_value = str(new_value).zfill(12)
                data[field_name] = new_value
                lines[i] = self.parser.format_line(data, record_type) + "\\n"
                updated = True
                break

        if updated:
            self.file_manager.write_lines(lines)
            self.update_footer(
                lines, self.transaction_counter, decimal.Decimal(new_value)
            )
        return updated

    def update_footer(self, lines, transaction_counter, amount):
        """Update the footer line with the new transaction count and control sum.

        Args:
            lines (list): The list of lines in the file.
            transaction_counter (int): The new transaction count.
            amount (decimal.Decimal): The amount of the new transaction.

        Raises:
            ValueError: If the footer is not found in the file.
        """
        try:
            footer_index, footer_data = self.find_footer(lines)
            footer_data["total_count"] = str(transaction_counter).zfill(6)
            current_control_sum = int(footer_data["control_sum"])
            additional_amount = int(amount * 100)
            footer_data["control_sum"] = str(
                current_control_sum + additional_amount
            ).zfill(12)
            lines[footer_index] = self.parser.format_line(footer_data, "FOOTER") + "\\n"
        except ValueError as e:
            logger.error("Error updating footer: %s", str(e))
            raise

    def find_footer(self, lines):
        """Find and return the footer line from the file lines.

        Args:
            lines (list): The list of lines in the file.

        Returns:
            tuple: The index of the footer line and the footer data.
        """
        for i in reversed(range(len(lines))):
            if "03" == lines[i][:2].strip():
                return i, self.parser.parse_line(lines[i], "FOOTER")
        logger.error("No footer found in the file.")
        raise ValueError("Footer not found in the file.")

    def initialize_transaction_counter(self):
        """Initialize the transaction counter by reading the existing records.

        Returns:
            int: The number of existing transactions.
        """
        lines = self.file_manager.read_lines()
        counter = 0
        for line in lines:
            if line.startswith("02"):
                counter += 1
        return counter

    def matches_transaction_counter(self, data, transaction_counter):
        """Check if the transaction counter in the data matches the provided transaction counter.

        Args:
            data (dict): The data dictionary.
            transaction_counter (str): The transaction counter to match.

        Returns:
            bool: True if the transaction counter matches, False otherwise.
        """
        return transaction_counter is None or data.get("counter", "").zfill(
            6
        ) == transaction_counter.zfill(6)
