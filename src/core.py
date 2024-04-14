"""
Core module for handling fixed-width files.
Provides the FixedWidthFile class for handling fixed-width file operations.
"""

import decimal
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
                if field_name == "amount":
                    try:
                        amount_in_cents = int(value)
                        data[field_name] = amount_in_cents
                    except decimal.InvalidOperation as exc:
                        logger.error(
                            "Invalid amount format: '%s' in line: '%s'", value, line
                        )
                        raise ValueError(f"Invalid amount format: '{value}'") from exc
                elif field_name == "currency":
                    allowed_currencies = ["USD", "EUR", "GBP"]
                    if value not in allowed_currencies:
                        logger.error(
                            "Invalid currency code: '%s' in line: '%s'", value, line
                        )
                        raise ValueError(f"Invalid currency code: '{value}'")
                    data[field_name] = value
                else:
                    data[field_name] = value
            else:
                data[field_name] = value
        if record_type == "TRANSACTION":
            self.transaction_counter += 1
            data["counter"] = f"{self.transaction_counter:06}"
        logger.debug("Parsed data for %s: %s", record_type, data)
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
            # Process each line based on the record type
            for line in content:
                clean_line = line.strip()
                if len(clean_line) == self.RECORD_LENGTH:
                    record_type = self._get_record_type(clean_line)
                    data = self._parse_line(clean_line, record_type)
                    self._validate_data(data, record_type)
                    self.data.setdefault(record_type, []).append(data)
                else:
                    logger.error("Invalid line length: %d", len(clean_line))
                    raise ValueError("Invalid line length.")
        except FileNotFoundError:
            logger.error("File not found: %s", self.filename)
            raise
        except Exception as e:
            logger.error("An error occurred while reading the file: %s", str(e))
            raise

    def _format_line(self, data, record_type):
        """
        Format a line based on the record type and field definitions.

        Args:
            data (dict): The data to format.
            record_type (str): The type of record (e.g., HEADER, TRANSACTION, FOOTER).

        Returns:
            str: The formatted line.
        """
        line = ""
        for field_name, (start, end) in self.FIELD_DEFINITIONS[record_type].items():
            value = str(data.get(field_name, ""))
            field_length = end - start
            if field_name == "amount":  # Numeric field, pad with zeros on the left
                formatted_value = value.zfill(field_length)
            else:
                formatted_value = value.ljust(field_length)
            line += formatted_value
        line += "\\n"
        return line

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
            with open(self.filename, "r", encoding="utf-8", newline="") as file:
                lines = file.read().splitlines()  # Removes newlines

            max_counter = 0
            for line in lines:
                if line.startswith("02"):
                    current_counter = int(line[2:8])
                    if current_counter > max_counter:
                        max_counter = current_counter
            new_transaction_counter = max_counter + 1

            amount_formatted = f"{int(amount * 100):012d}"  # 12 digits
            new_transaction = {
                "field_id": "02",
                "counter": f"{new_transaction_counter:06d}",
                "amount": amount_formatted,
                "currency": currency,
                "reserved": " " * 93,  # Adjusted padding
            }

            # Format and insert new transaction line before the footer
            footer_index = len(lines) - 1
            new_transaction_line = self._format_line(new_transaction, "TRANSACTION")
            print(new_transaction_line)
            lines.insert(footer_index, new_transaction_line)

            # Update footer with the new total count and new control sum
            footer_data = self._parse_line(lines[footer_index + 1], "FOOTER")
            footer_data["total_count"] = f"{new_transaction_counter:06d}"
            current_control_sum = int(footer_data["control_sum"])
            added_amount = int(amount * 100)
            footer_data["control_sum"] = f"{current_control_sum + added_amount:012d}"
            updated_footer_line = self._format_line(footer_data, "FOOTER")
            lines[footer_index + 1] = updated_footer_line

            with open(self.filename, "w", encoding="utf-8", newline="") as file:
                file.write("\n".join(lines))  # Ensure each line ends with a newline

            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to add transaction: %s", str(e))
            return False

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
        updated = False
        try:
            with open(self.filename, "r+", encoding="utf-8") as file:
                lines = file.readlines()
                file.seek(0)
                for index, line in enumerate(lines):
                    if len(line.strip()) == self.RECORD_LENGTH:
                        record_type = self._get_record_type(line.strip())
                        data = self._parse_line(line.strip(), record_type)

                        if (
                            transaction_counter
                            and record_type == "TRANSACTION"
                            and data["counter"] == transaction_counter
                        ):
                            if field_name == "amount":
                                value_in_cents = int(float(value) * 100)
                                data[field_name] = f"{value_in_cents:012d}"
                                updated = True
                            elif field_name in data:
                                data[field_name] = value
                                updated = True

                        # Reformat the line whether updated or not to maintain the file structure
                        formatted_line = self._format_line(data, record_type) + "\n"
                        lines[index] = formatted_line

                if updated:
                    file.seek(0)
                    file.writelines(lines)
                    file.truncate()
            return updated
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to set value: %s", e)
            return False
