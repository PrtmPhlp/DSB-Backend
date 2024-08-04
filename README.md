This project focuses on retrieving existing representation plans, further processing them with sorting mechanisms and abbreviation replacements, and visualizing them on an outsourced Next.js / Static Website. The project is specifically tailored to integrate with the [DSBMobile](https://www.dsbmobile.de/) system and the [DAVINCI](https://davinci.stueber.de/) layout scheme by [Stübner Systems](https://www.stueber.de/).

The process involves the following steps:

1. Authentication through API.
2. Retrieving all currently available representation plans.
3. Fetching data and exporting **only** the requested course as a markup format, such as JSON, a Python list, or even a [PKL](https://pkl-lang.org/index.html) file.
4. Creating a second processed version for easier readability, with the following modifications:
    - Replacing teacher abbreviations.
    - Replacing subject abbreviations.
    - ...
5. Exporting data to either a _Static Website_ **or** a _Next.js Website_, utilizing a _real_ backend (with features like request handling, spam protection, on-load data fetching, etc.).