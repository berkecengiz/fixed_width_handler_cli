
# Fixed Width Handler CLI

Command line interface (CLI) application for handling fixed width files.

## Installation

This project utilizes [Poetry](https://python-poetry.org/) for dependency management. To set up the project and install its dependencies, execute the following command:

```bash
poetry install
```

## Usage

### General Command Structure

The CLI supports multiple operations. Here is the general command structure:

```bash
poetry run cli [command] [options]
```

### Available Commands

- **Get**: Retrieve the value of a specified field from a fixed-width file.
- **Set**: Update the value of a specified field in a fixed-width file.
- **Add**: Add a new transaction to a fixed-width file.

**Example**:

```bash
poetry run cli get sample.fwf name
poetry run cli get sample.fwf TRANSACTION amount --transaction_counter 000004
poetry run cli set sample.fwf HEADER address "123 New Address"
poetry run cli set sample.fwf TRANSACTION amount 10 --transaction_counter 000003
poetry run cli add sample.fwf 500.00 USD
```

## Testing

Tests are located in the `tests` directory. Execute the following command to run all tests:

```bash
poetry run pytest
```

## Linting and Formatting

- **Linting**: This project uses `Pylint` to identify bugs and style problems in Python source code. To run Pylint:

  ```bash
  poetry run pylint src tests
  ```

- **Formatting**: `Black` is used to ensure consistent code formatting. To format your code:

  ```bash
  poetry run black src tests
  ```
