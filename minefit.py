from pprint import pprint
from typing import Dict
import json
import time
import os
import re

import requests
from bs4 import BeautifulSoup


def parse_page(page: str) -> Dict:
    result = {}
    page = page.decode('utf-8')

    # Fix page first - there are missing opening <tr> tags
    page = re.sub(r'</tr>', '</tr><tr>', page)

    soup = BeautifulSoup(page, "html.parser")
    for course in soup.find_all('tr'):
        children = course.findChildren()
        if not children:
            continue

        try:
            department = int(children[0].text)
        except ValueError:
            continue  # Skip rows that do not contain number as their department

        course_id = children[1].text
        course_name = children[2].text
        enrolled = int(children[3].text)
        finished = int(children[4].text)
        submitted_survey = int(children[5].text)
        percent_finished = finished / enrolled

        result[course_id] = {
            'department': department,
            'course_id': course_id,
            'course_name': course_name,
            'enrolled': enrolled,
            'finished': finished,
            'submitted_survey': submitted_survey,
            'percent_finished': percent_finished
        }

    return result


def fetch_courses():
    page = fetch_page()
    courses = parse_page(page)

    return courses


def fetch_page():
    response = requests.get('https://anketa.cvut.cz/stav/stav_anketa_fit.html')
    response.raise_for_status()

    return response.content


def read_data(fn):
    with open(fn, encoding='utf-8') as f:
        data = json.load(f)

    return data


def save_data(fn, data):
    with open(f"{fn}.temp", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if os.path.exists(fn):
        os.remove(fn)

    os.rename(f"{fn}.temp", fn)


def save_courses(courses, fn='courses.json'):
    timestamp = int(time.time())

    if os.path.exists(fn):
        data = read_data(fn)
    else:
        data = {}

    data[timestamp] = courses
    save_data(fn, data)


def main():
    courses = fetch_courses()
    save_courses(courses)


if __name__ == '__main__':
    main()
