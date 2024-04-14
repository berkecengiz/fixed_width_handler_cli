"""
Core module for handling fixed-width files.
Provides the FixedWidthFile class for handling fixed-width file operations.
"""

import logging

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
    ALLOWED_CURRENCIES = ["USD", "EUR", "GBP"]

    def __init__(self, filename):
        """
        Initialize the FixedWidthFile object with a file name.

        Args:
            filename (str): The name of the fixed-width file.
        """
        self.filename = filename
        self.data = {}
        self.transaction_counter = 0
        logger.debug("FixedWidthFile initialized for file: %s", filename)

    def read(self):
        """
        Read and process the fixed-width file, handling newline characters.

        Raises:
            FileNotFoundError: If the file is not found.
            ValueError: If an error occurs while reading the file.
        """
        logger.info("Reading file: %s", self.filename)
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                content = file.readlines()
            self._process_content(content)
        except FileNotFoundError:
            logger.error("File not found: %s", self.filename)
            raise
        except Exception as e:
            logger.error("An error occurred while reading the file: %s", str(e))
            raise

    def set_value(self, field_name, value, transaction_counter=None):
        """
        Set the value of a field in a fixed-width file for a specific transaction.

        Args:
            field_name (str): The field name to update.
            value (str): The new value to set.
            transaction_counter (str, optional): The transaction counter to filter by.

        Returns:
            bool: True if the value was successfully updated, False otherwise.
        """
        try:
            lines = self._read_file_lines()
            updated = self._update_field_in_lines(
                lines, field_name, value, transaction_counter
            )
            if updated:
                self._write_file_lines(lines)
            return updated
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to set value: %s", e)
            return False

    def add_transaction(self, amount, currency):
        """
        Adds a new transaction to the fixed-width file.

        Args:
            amount (decimal.Decimal): The amount of the transaction.
            currency (str): The currency code for the transaction.

        Returns:
            bool: True if the transaction was successfully added, False otherwise.
        """
        try:
            lines = self._read_file_lines()
            new_transaction_counter = self._get_new_transaction_counter(lines)
            new_transaction = self._create_new_transaction(
                amount, currency, new_transaction_counter
            )
            lines = self._insert_new_transaction(lines, new_transaction)
            lines = self._update_footer(lines, new_transaction_counter, amount)
            self._write_file_lines(lines)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to add transaction: %s", str(e))
            return False

    def _get_record_type(self, line):
        """
        Identify the type of record based on its field ID.

        Args:
            line (str): The line to parse.

        Returns:
            str: The record type (e.g., HEADER, TRANSACTION, FOOTER).
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

        Args:
            line (str): The line to parse.
            record_type (str): The type of record (e.g., HEADER, TRANSACTION, FOOTER).

        Returns:
            dict: A dictionary containing the parsed data.
        """
        data = {}
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = line[start:end].strip()
            if record_type == "TRANSACTION":
                data = self._parse_transaction_field(field_name, value, line, data)
            else:
                data[field_name] = value

        if record_type == "TRANSACTION":
            self.transaction_counter += 1
            data["counter"] = f"{self.transaction_counter:06}"

        logger.debug("Parsed data for %s: %s", record_type, data)
        return data

    def _parse_transaction_field(self, field_name, value, line, data):
        """
        Parse a field from a transaction record.

        Args:
            field_name (str): The name of the field.
            value (str): The value of the field.
            line (str): The line being parsed.
            data (dict): The dictionary to store the parsed data.

        Returns:
            dict: The updated data dictionary.
        """
        if field_name == "amount":
            data = self._parse_amount_field(value, line, data)
        elif field_name == "currency":
            data = self._parse_currency_field(value, line, data)
        else:
            data[field_name] = value
        return data

    def _parse_amount_field(self, value, line, data):
        """
        Parse an amount field from a transaction record.

        Args:
            value (str): The value of the field.
            line (str): The line being parsed.
            data (dict): The dictionary to store the parsed data.

        Returns:
            dict: The updated data dictionary.
        """
        try:
            amount_in_cents = int(value)
            data["amount"] = amount_in_cents
        except ValueError as exc:
            logger.error("Invalid amount format: '%s' in line: '%s'", value, line)
            raise ValueError(f"Invalid amount format: '{value}'") from exc
        return data

    def _parse_currency_field(self, value, line, data):
        """
        Parse a currency field from a transaction record.

        Args:
            value (str): The value of the field.
            line (str): The line being parsed.
            data (dict): The dictionary to store the parsed data.

        Returns:
            dict: The updated data dictionary.
        """
        if value not in self.ALLOWED_CURRENCIES:
            logger.error("Invalid currency code: '%s' in line: '%s'", value, line)
            raise ValueError(f"Invalid currency code: '{value}'")
        data["currency"] = value
        return data

    def _validate_data(self, data, record_type):
        """
        Validate parsed data based on the record type.

        Args:
            data (dict): The parsed data to validate.
            record_type (str): The type of record (e.g., HEADER, TRANSACTION, FOOTER).
        """
        if record_type == "TRANSACTION":
            allowed_currencies = ["USD", "EUR", "GBP"]
            if data["currency"] not in allowed_currencies:
                logger.error("Invalid currency code: %s", data["currency"])
                raise ValueError(f"Invalid currency code: {data['currency']}")

    def _format_line(self, data, record_type):
        """
        Format a line based on the record type and field definitions.

        Args:
            data (dict): The data to format.
            record_type (str): The type of record (e.g., HEADER, TRANSACTION, FOOTER).

        Returns:
            str: The formatted line.
        """
        formatted_fields = []
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = str(data.get(field_name, ""))
            field_length = end - start
            formatted_value = self._format_field_value(field_name, value, field_length)
            formatted_fields.append(formatted_value)
        line = "".join(formatted_fields) + "\\n"
        return line

    def _format_field_value(self, field_name, value, field_length):
        """
        Format a field value based on its name and length.

        Args:
            field_name (str): The name of the field.
            value (str): The value of the field.
            field_length (int): The length of the field.

        Returns:
            str: The formatted field value.
        """
        if field_name == "amount":  # Numeric field, pad with zeros on the left
            return value.zfill(field_length)
        else:
            return value.ljust(field_length)

    def _process_content(self, content):
        """
        Process each line in the content based on the record type.

        Args:
            content (list): The content to process.
        """
        for line in content:
            clean_line = line.strip()
            if len(clean_line) == self.RECORD_LENGTH:
                self._process_line(clean_line)
            else:
                logger.error("Invalid line length: %d", len(clean_line))
                raise ValueError("Invalid line length.")

    def _process_line(self, line):
        """
        Process a line based on the record type.

        Args:
            line (str): The line to process.
        """
        record_type = self._get_record_type(line)
        data = self._parse_line(line, record_type)
        self._validate_data(data, record_type)
        self.data.setdefault(record_type, []).append(data)

    def _read_file_lines(self):
        """Read the lines of the file and return them as a list."""
        with open(self.filename, "r", encoding="utf-8", newline="") as file:
            return file.read().splitlines()  # Removes newlines

    def _get_new_transaction_counter(self, lines):
        """Get the new transaction counter based on the existing transactions."""
        max_counter = max(
            (int(line[2:8]) for line in lines if line.startswith("02")),
            default=0,
        )
        return max_counter + 1

    def _create_new_transaction(self, amount, currency, counter):
        """Create a new transaction dictionary with the given data.

        Args:
            amount (decimal.Decimal): The amount of the transaction.
            currency (str): The currency code for the transaction.
            counter (int): The transaction counter.

        Returns:
            dict: The new transaction data.
        """
        amount_formatted = f"{int(amount * 100):012d}"  # 12 digits
        return {
            "field_id": "02",
            "counter": f"{counter:06d}",
            "amount": amount_formatted,
            "currency": currency,
            "reserved": " " * 93,  # Adjusted padding
        }

    def _insert_new_transaction(self, lines, transaction):
        """
        Insert a new transaction line before the footer.

        Args:
            lines (list): The list of lines in the file.
            transaction (dict): The new transaction data.
        """
        footer_index = len(lines) - 1
        new_transaction_line = self._format_line(transaction, "TRANSACTION")
        lines.insert(footer_index, new_transaction_line)
        return lines

    def _update_footer(self, lines, counter, amount):
        """
        Update the footer line with the new transaction count and control sum.

        Args:
            lines (list): The list of lines in the file.
            counter (int): The new transaction counter.
            amount (decimal.Decimal): The amount of the new transaction.

        Returns:
            list: The updated list of lines.
        """
        footer_index = len(lines) - 1
        footer_data = self._parse_line(lines[footer_index], "FOOTER")
        footer_data["total_count"] = f"{counter:06d}"
        current_control_sum = int(footer_data["control_sum"])
        added_amount = int(amount * 100)
        footer_data["control_sum"] = f"{current_control_sum + added_amount:012d}"
        updated_footer_line = self._format_line(footer_data, "FOOTER")
        lines[footer_index] = updated_footer_line
        return lines

    def _write_file_lines(self, lines):
        """Write the lines to the file.

        Args:
            lines (list): The list of lines to write.
        """
        with open(self.filename, "w", encoding="utf-8", newline="") as file:
            file.write("\n".join(lines))  # Each line ends with a newline

    def _update_field_in_lines(self, lines, field_name, value, transaction_counter):
        updated = False
        for index, line in enumerate(lines):
            clean_line = line.strip()
            if len(clean_line) == self.RECORD_LENGTH:
                record_type = self._get_record_type(clean_line)
                data = self._parse_line(clean_line, record_type)
                updated = self._update_field_in_data(
                    data, field_name, value, transaction_counter, record_type
                )
                lines[index] = self._format_line(data, record_type) + "\n"
        return updated

    def _update_field_in_data(
        self, data, field_name, value, transaction_counter, record_type
    ):
        if (
            transaction_counter
            and record_type == "TRANSACTION"
            and data["counter"] == transaction_counter
        ):
            if field_name == "amount":
                value_in_cents = int(float(value) * 100)
                data[field_name] = f"{value_in_cents:012d}"
                return True
            elif field_name in data:
                data[field_name] = value
                return True
        return False
