# pylint: disable=invalid-name
"""
PyDSB Module

This module provides classes and methods for interacting with DSB mobile API.
"""

import logging
import sys
import requests

BASE_URL = "https://mobileapi.dsbcontrol.de"

logger = logging.getLogger(__name__)


class PyDSB:
    """
    A class to interact with the DSB mobile API.

    Provides methods to authenticate with the API using credentials, and retrieve data such as 
    plans, news, and postings.

    Attributes:
        token (str): Authentication token obtained after successful authentication.

    Methods:
        __init__(self, username: str = None, password: str = None):
            Initializes the PyDSB instance with username and password to authenticate with the API.

        get_plans(self) -> list:
            Retrieves the list of plans (timetables) available for the authenticated user.

        get_news(self) -> list:
            Retrieves the list of news items from the DSB API.

        get_postings(self) -> list:
            Retrieves the list of postings (documents) available for the authenticated user.
    """

    def __init__(self, username: str = None, password: str = None): # type: ignore
        """
        Initialize PyDSB with username and password to authenticate and obtain a token.

        :param username: Username for DSB authentication.
        :param password: Password for DSB authentication.
        """
        params = {
            "bundleid": "de.heinekingmedia.dsbmobile",
            "appversion": "35",
            "osversion": "22",
            "pushid": "",
            "user": username,
            "password": password
        }

        r = requests.get(BASE_URL + "/authid", params=params, timeout=10)

        if r.text == "\"\"":  # Me when http status code is always 200 :trollface:
            logger.critical("PyDSB: Invalid Credentials!")
            sys.exit(1)
            # raise Exception("Invalid Credentials")
        else:
            self.token = r.text.replace("\"", "")

    def get_plans(self) -> list:
        """
        Fetches plans from DSB API.

        :return: List of dictionaries representing plans.
        """
        raw_plans = requests.get(BASE_URL + "/dsbtimetables",
                                 params={"authid": self.token}, timeout=10).json()
        plans = []
        preview_url_base: str = "https://light.dsbcontrol.de/DSBlightWebsite/Data/"

        for plan in raw_plans:
            for i in plan["Childs"]:
                plans.append({
                    "id": i["Id"],
                    "is_html": i["ConType"] == 6,
                    "uploaded_date": i["Date"],
                    "title": i["Title"],
                    "url": i["Detail"],
                    "preview_url": f"{preview_url_base}{i['Preview']}",
                })

        return plans

    def get_news(self) -> list:
        """
        Fetches news from DSB API.

        :return: List of dictionaries representing news items.
        """
        raw_news = requests.get(BASE_URL + "/newstab",
                                params={"authid": self.token}, timeout=10).json()
        news = []

        for i in raw_news:
            news.append({
                "title": i["Title"], "date": i["Date"], "content": i["Detail"]
            })

        return news

    def get_postings(self) -> list:
        """
        Fetches postings from DSB API.

        :return: List of dictionaries representing postings.
        """
        raw_postings = requests.get(BASE_URL + "/dsbdocuments",
                                    params={"authid": self.token}, timeout=10).json()
        postings = []
        preview_url_base: str = "https://light.dsbcontrol.de/DSBlightWebsite/Data/"

        for posting in raw_postings:
            for i in posting["Childs"]:
                postings.append({
                    "id": i["Id"],
                    "uploaded_date": i["Date"],
                    "title": i["Title"],
                    "url": i["Detail"],
                    "preview_url": f"{preview_url_base}{i['Preview']}",
                })

        return postings
