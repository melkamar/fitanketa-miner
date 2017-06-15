import json
import os
import re
import time
import datetime
from typing import Dict, List, Union

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
    if not os.path.exists(os.path.dirname(fn)):
        os.mkdir(os.path.dirname(fn))

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


def make_md_table(semester: str, course_semester_data: List[Dict[str, Union[str, int, float]]]):
    """ Make markdown table from data of a single semester-course. """
    if not course_semester_data:
        return ""

    data_item = course_semester_data[0]
    course_id = data_item['course_id']
    course_name = data_item['course_name']
    enrolled_total = data_item['enrolled']

    row_headers = '|                          |'
    row_separator = '|--------------------------|'
    row_completed_total = "|**Splněno celkem**        |"
    row_completed_total_percent = "|**Splněno celkem procent**|"

    row_data_headers = []
    row_data_separator = []
    row_data_compl_total = []
    row_data_compl_total_percent = []

    previous_completed = 0
    previous_completed_percent = 0

    for datapoint in course_semester_data:
        row_data_headers.append(util.timestamp_to_date_str(datapoint['timestamp']))
        row_data_separator.append("-"*20)

        new_completed = datapoint['finished']
        new_completed_percent = datapoint['percent_finished']
        completed_delta = new_completed-previous_completed
        completed_percent_delta = new_completed_percent-previous_completed_percent
        previous_completed = new_completed
        previous_completed_percent = new_completed_percent

        row_data_compl_total.append(f'''{new_completed} ({completed_delta:+})''')
        row_data_compl_total_percent.append(f'''{datapoint['percent_finished']*100:.0f}% ({completed_percent_delta*100:+.0f}%)''')

    print("ha")
    md = f"""## {course_name} ({course_id})

**Semestr**: {semester}

**Přihlášeno studentů**: {enrolled_total}

{row_headers}{"|".join(row_data_headers)}|
{row_separator}{"|".join(row_data_separator)}|
{row_completed_total}{"|".join(row_data_compl_total)}|
{row_completed_total_percent}{"|".join(row_data_compl_total_percent)}|
"""

    return md


def load_semester(semester: str):
    fn = f'data/{semester.upper()}.json'
    if not os.path.exists(fn):
        return {}

    return read_data(fn)


def parse_course_data(course_id: str, data):
    study_programme = course_id.split('-', maxsplit=1)[0]
    if not data:
        return []

    try:
        course_data = data[study_programme]
        course_data = course_data[course_id]
        return course_data
    except KeyError:
        return []


def merge_single_course(new_course_data, original_data, timestamp):
    new_course_id = new_course_data['course_id']
    new_course_data['timestamp'] = timestamp

    original_course_data = parse_course_data(new_course_id, original_data)
    study_programme = new_course_id.split('-', maxsplit=1)[0]

    if not original_course_data:
        # create course data
        if study_programme not in original_data:
            original_data[study_programme] = {}

        original_data[study_programme][new_course_id] = [new_course_data]

    else:
        # there already is some data for this course
        # check if this new data adds anything of value and add it only if necessary
        data = original_data[study_programme][new_course_id][-1]
        finished_original = data['finished']
        finished_new = new_course_data['finished']
        if finished_new != finished_original:
            original_data[study_programme][new_course_id].append(new_course_data)


def add_new_course_data(new_data, original_data, timestamp):
    for course_data in new_data.values():
        merge_single_course(course_data, original_data, timestamp)


import util


def main():
    now = datetime.datetime.now()
    semester = util.get_semester(now)

    old_data = load_semester(semester)
    courses = fetch_courses()
    add_new_course_data(courses, old_data, now.timestamp())

    fn = f'data/{semester.upper()}.json'
    save_data(fn, old_data)

    for semester_programme, semester_courses in old_data.items():
        for course_id, course_data in semester_courses.items():
            md_page = make_md_table(semester, course_data)
            print(md_page)
            return


if __name__ == '__main__':
    main()
