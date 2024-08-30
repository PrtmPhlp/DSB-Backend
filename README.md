# DSBMobile Webscraper

[![CodeQL](https://github.com/PrtmPhlp/DSBMobile/actions/workflows/codeql.yml/badge.svg)](https://github.com/PrtmPhlp/DSBMobile/actions/workflows/codeql.yml)

This project is focused on retrieving existing representation plans, processing them with sorting mechanisms, abbreviation replacements, and other modifications, and exporting them in a format suitable for further processing.

Additionally, this project aims to visualize the gathered data on an external Next.js / Static Website to provide a personalized user experience. The project is currently highly tailored to integrate with the [DSBMobile](https://www.dsbmobile.de/) system and the [DAVINCI](https://davinci.stueber.de/) layout scheme by [Stüber Systems](https://www.stueber.de/).

> [!NOTE]
> The following steps may not be entirely accurate, as the project is still under active development.

The process involves the following steps:

1. Authenticating through the API.
2. Retrieving all currently available representation plans.
3. Fetching data and exporting **only** the requested course in a markup format, such as _(currently)_ JSON, a Python list, or possibly in the future, the [PKL](https://pkl-lang.org/index.html) markup format.
4. Creating a second processed version for easier readability, with the following modifications:
    - Replacing teacher abbreviations.
    - Replacing subject abbreviations.
    - ...
5. Exporting data to either a _Static Website_ **or** a _Next.js Website_, utilizing a _real_ backend (with features like request handling, spam protection, on-load data fetching, etc.).


## Usage

> [!WARNING]
> This project is still under active development and may not be ready for use yet.

```console
$ python src/scraper.py -h

Usage: python src/scraper.py [-h] [-v] [-c [COURSE]] [-p] [--version]

     ___      ___  ___ ___
    | _ \_  _|   \/ __| _ )
    |  _/ || | |) \__ \ _ \
    |_|  \_, |___/|___/___/
         |__/

This script scrapes data from dsbmobile.com to retrieve class replacements.

Options:
  -h, --help            show this help message and exit
  -v, --verbose         Set the verbosity level: 0 for CRITICAL, 1 for INFO, 2
                        for DEBUG
  -c, --course [COURSE]
                        Select the course to scrape. Default: MSS12
  -p, --print-output    Print output to console
  --version             show program's version number and exit

```

### Prerequisites

Before you begin, ensure you have Python installed on your machine. You can download it from the official [Python website](https://www.python.org/downloads/). This project was developed using Python 3.12.4, so no guarantees are made for other versions.

### Setting Up the Virtual Environment

1. **Clone the repository**:

    ```bash
    git clone https://github.com/PrtmPhlp/DSBMobile.git
    cd DSBMobile
    ```

2. **Create a virtual environment**:

    ```bash
    python3 -m venv .venv
    ```

3. **Activate the virtual environment**:

    On macOS and Linux:
    ```bash
    source .venv/bin/activate
    ```

    On Windows:
    ```bash
    .\.venv\Scripts\activate
    ```

4. **Install the required packages**:

    Ensure you are in the project directory where the `requirements.txt` file is located, then run:

    ```bash
    pip install -r requirements.txt
    ```

### Secrets Management

This project requires a username and password to authenticate with the DSBMobile API. You can set these in the `.env` file or as environment variables. If you choose to set them in the `.env` file, clone the `.env.sample` file and rename it to `.env`.

```bash
cp .env.sample .env
```

Now edit the `DSB_USERNAME` and `DSB_PASSWORD` placeholders with your actual credentials.

```bash
DSB_USERNAME=your_username
DSB_PASSWORD=your_password
```

If you prefer to set them as environment variables, use the following command, depending on your operating system:

On macOS and Linux:
```bash
export DSB_USERNAME=your_username
export DSB_PASSWORD=your_password
```

### Running the Application

Once the virtual environment is set up, dependencies are installed, and secrets are configured, you can run the application using:

```bash
python src/scraper.py
```

For help running the application, use the `--help` flag:

```bash
python src/scraper.py --help
```

## Contributing

Contributions are welcome! If you find a bug or have a suggestion for improvement, please open an issue or submit a pull request on the GitHub repository.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.