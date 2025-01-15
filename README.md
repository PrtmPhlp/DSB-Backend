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

- Python 3.12.4 (maybe other versions work, but this is what I used to develop this project)

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
or
```bash
python src/runner.py
```

For help running the application, use the `--help` flag:

```bash
python src/scraper.py --help
```
...or
```bash
python src/runner.py --help
```

### Sample output
<details>
<summary>Click to expand</summary>

```json
{
	"createdAt": "2024-08-31T21:45:26.027867",
	"class": "MSS12",
	"substitution": [
		{
			"id": "1",
			"date": "02-09-2024",
			"weekDay": [
				"1",
				"Montag"
			],
			"content": [
				{
					"position": "6.",
					"teacher": "(xy)",
					"subject": "xy",
					"room": "123",
					"topic": "...",
					"info": "..."
				}
			]
		},
		{
			"id": "2",
			"date": "03-09-2024",
			"weekDay": [
				"2",
				"Dienstag"
			],
			"content": [
				{
					"position": "6.",
					"teacher": "(xy)",
					"subject": "xy",
					"room": "123",
					"topic": "...",
					"info": "..."
				},
				{
					"position": "6.",
					"teacher": "(xy)",
					"subject": "xy",
					"room": "123",
					"topic": "...",
					"info": "..."
				}
			]
		}
	]
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
