This project is dedicated to fetching already existent representation plans, processing them further with sorting mechanisms and abbreviation replacements and visualizing them on a outsourced Next.js / Static Website. This Project is highly personalized to the Website system [DSBMobile](https://www.dsbmobile.de/) and Layout scheme [DAVINCI](https://davinci.stueber.de/) by [Stübner Systems](https://www.stueber.de/)
The following process should be achieved:

1. Auth through API
2. Get all currently available representation plans
3. Fetch data and export **only** the requested course as markup, e. g. json, python list or maybe even as a [pkl](https://pkl-lang.org/index.html) file
4. create a second processed version for easier readability with following aspects:
    - Teacher abbreviation replacement
    - Subject abbreviation replacement
    - ...
5. export data to either _static Website_ **or** _nextjs Website_ using _real_ backend (w/ requesting support, spam protection, onload fetch etc.)
