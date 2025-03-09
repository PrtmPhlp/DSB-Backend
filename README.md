# DSBMobile Webscraper

A Python-based web scraper for DSBMobile, designed to fetch and process representation plans


[![CodeQL](https://github.com/PrtmPhlp/DSBMobile/actions/workflows/codeql.yml/badge.svg)](https://github.com/PrtmPhlp/DSBMobile/actions/workflows/codeql.yml)

This project is focused on retrieving existing representation plans, processing them and exporting them in a format suitable for further processing.

Additionally, this project aims to visualize the gathered data on an external Next.js Webpage to provide a personalized user experience. The project is currently highly tailored to integrate with the [DSBMobile](https://www.dsbmobile.de/) system and the [DAVINCI](https://davinci.stueber.de/) layout scheme by [Stüber Systems](https://www.stueber.de/).


> [!NOTE]
> Link to NEXT.js [frontend](https://github.com/prtmphlp/dsb-frontend)

## Usage

There are three main ways to use this project:

1. **Recommended:** As a Docker container / stack integrated with the [frontend](https://github.com/prtmphlp/dsb-frontend)
2. As a standalone Python script
3. As a Flask API

## 🐳 Docker

> [!WARNING]
> Currently, the Docker image is only available for ARM64 architecture.

There are three ways to run the Docker container:

### 1. Running the fullstack Docker Compose stack:

Clone the repository and create a `.env` file with your credentials:

```bash
cp .env.sample .env
```

fill in the `DSB_USERNAME` and `DSB_PASSWORD` fields with your credentials.

and run:

```bash
docker compose up -d
```

this will build the dsb-scraper image and download the dsb-frontend image from my provided [Docker Image](https://github.com/users/PrtmPhlp/packages/container/package/dsb-frontend).

### 2. Running the fullstack Docker Compose stack but building all images yourself:

If you want to build all images yourself, you can do so by following this folder structure:

```
fullstack
├── backend (this repository)
└── frontend (https://github.com/prtmphlp/dsb-frontend)
```

and running from the `backend` folder:

```bash
docker compose up -d --build
```

### 3. Running the backend only:

```bash
docker compose -f compose-backend.yaml up -d
```

## Running the standalone Python Script

<details>
<summary>Click to expand</summary>

```console
$ python src/main.py -h

Usage: python scraper.py [-h] [-v] [--env-file ENV_FILE] [--raw-file RAW_FILE] [--output-formatted-file OUTPUT_FORMATTED_FILE] [--teacher-dict TEACHER_DICT] [--teacher-replaced-file TEACHER_REPLACED_FILE]
                         [--schema-file SCHEMA_FILE] [--skip-validator] [-p]

     ___      ___  ___ ___
    | _ \_  _|   \/ __| _ )
    |  _/ || | |) \__ \ _ \
    |_|  \_, |___/|___/___/
         |__/

Scrape day-plans once per day, attach empty-first-column lines to the last course.

Options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable DEBUG logging.
  --env-file ENV_FILE   Path to the .env file.
  --raw-file RAW_FILE   Where to save the raw day-based data.
  --output-formatted-file OUTPUT_FORMATTED_FILE
                        Where to save the formatted multi-course JSON.
  --teacher-dict TEACHER_DICT
                        Path to the teacher dictionary file.
  --teacher-replaced-file TEACHER_REPLACED_FILE
                        Where to save the teacher-replaced JSON.
  --schema-file SCHEMA_FILE
                        Path to the JSON schema file.
  --skip-validator      Skip JSON schema validation.
  -p, --print-output    Print raw day-based JSON output.
```

### Prerequisites

- Python 3.13 (maybe other versions work, but this is what I used to develop this project)

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
python src/main.py
```

For help running the application, use the `--help` flag:

```bash
python src/main.py --help
```

### Sample output
<details>
<summary>Click to expand</summary>

```json
{
    "createdAt": "2025-03-09T11:56:55.303724",
    "courses": {
        "10a": {
            "substitution": [
                {
                    "id": "1",
                    "date": "13-03-2025",
                    "weekDay": [
                        "Donnerstag"
                    ],
                    "content": [
                        {
                            "position": "4.",
                            "teacher": "(...)",
                            "subject": "D",
                            "room": "103",
                            "topic": "Vertretung",
                            "info": ""
                        }
                    ]
                },
                {
                    "id": "2",
                    "date": "10-03-2025",
                    "weekDay": [
                        "Montag"
                    ],
                    "content": [
                        {
                            "position": "5.",
                            "teacher": "(...)",
                            "subject": "Ge",
                            "room": "103",
                            "topic": "Anderer Unterricht",
                            "info": ""
                        },
                        {
                            "position": "5.",
                            "teacher": "...",
                            "subject": "E",
                            "room": "103",
                            "topic": "Zusatzunterricht",
                            "info": ""
                        }
                    ]
                }
            ]
		},
        "MSS13": {
            "substitution": [
                {
                    "id": "1",
                    "date": "12-03-2025",
                    "weekDay": [
                        "Mittwoch"
                    ],
                    "content": [
                        {
                            "position": "4.",
                            "teacher": "...",
                            "subject": "Mu",
                            "room": "Aula",
                            "topic": "Selbststudium",
                            "info": ""
                        },
                        {
                            "position": "5.",
                            "teacher": "...",
                            "subject": "Mu",
                            "room": "Aula",
                            "topic": "Zusatzunterricht",
                            "info": ""
                        }
                    ]
                }
            ]
        }
    }
}
```
</details>
</details>

## Running the Flask API

Setup should similar to the standalone Python script

run `python src/app.py`

## Contributing

Contributions are welcome! If you find a bug or have a suggestion for improvement, please open an issue or submit a pull request on the GitHub repository.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
