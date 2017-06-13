from pprint import pprint
from typing import Dict
import json
import time
import os
import re

import requests
from bs4 import BeautifulSoup

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates
import matplotlib.pyplot as plt


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


def combine_courses(courses, fn='courses.json'):
    timestamp = int(time.time())

    if os.path.exists(fn):
        data = read_data(fn)
    else:
        data = {}

    data[timestamp] = courses
    return data


def save_courses(data, fn='courses.json'):
    save_data(fn, data)


import datetime


def get_day_changes(courses):
    """
    Transform given courses data into a dict:
    {
        course_id: {
            day: course_data,    # day is datetime object
            day: course_data ...
        }
    }
    :param courses:
    :return:
    """
    res = {}

    for ts, content in courses.items():
        ts_date = datetime.datetime.fromtimestamp(int(ts))

        for course_id, course_data in content.items():
            if course_id not in res:
                res[course_id] = {}

            # Join timestamp on days
            day_date = ts_date + datetime.timedelta(
                # hours=-ts_date.hour,
                minutes=-ts_date.minute,
                seconds=-ts_date.second
            )
            if day_date not in res[course_id]:
                res[course_id][day_date] = 0

            res[course_id][day_date] = course_data

    return res


def plot_dates_values(date_val_dict: Dict[datetime.datetime, int], fn):
    """

    :param date_val_dict: Dictionary {datetime: num, datetime: num, datetime: num}
    :return:
    """
    if not os.path.exists('figs'):
        os.mkdir('figs')

    dates = matplotlib.dates.date2num(list(date_val_dict.keys()))
    vals = list(date_val_dict.values())
    plt.plot_date(dates, vals, linestyle='solid')
    plt.ylabel('Počet studentů')
    plt.savefig(f'figs/{fn}.png')


def make_md_table(course_datevals: Dict[datetime.datetime, Dict]):
    """ Make markdown table with student data"""
    if not course_datevals:
        return ""

    data_item = next(iter(course_datevals.values()))
    course_id = data_item['course_id']
    course_name = data_item['course_name']

    row_headers = '|                          |'
    row_separator = '|--------------------------|'
    row_completed_interval = "|**Splněno v období**      |"
    row_completed_total = "|**Splněno celkem**        |"
    row_completed_total_percent = "|**Splněno celkem procent**|"

    md = f"""##{course_name} ({course_id})
{row_headers}
{row_separator}
{row_completed_interval}
{row_completed_total}
{row_completed_total_percent}
    """


def main():
    # courses = fetch_courses()
    # combined = combine_courses(courses)
    # save_courses(combined)

    combined = combine_courses({})

    changes = get_day_changes(combined)
    print(changes['BI-LIN'])

    for course_id, course_data in changes.items():
        make_md_table(course_data)
        break


if __name__ == '__main__':
    main()
