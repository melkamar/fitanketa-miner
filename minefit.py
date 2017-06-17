import argparse
import logging
import time
import datetime
import json
import math
import os
import re
import shutil
import stat
from distutils.dir_util import copy_tree
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup
from git import Repo

import util


class SiteGenerator:
    def __init__(self, index_root, courses_root, data, semester):
        super().__init__()
        self.index_root = index_root
        self.courses_root = courses_root
        self.data = data
        self.semester = semester

    def generate_page(self):
        self._make_pages(6)
        self._make_index()

    def _make_index(self):
        if not os.path.exists(self.courses_root):
            raise ValueError(f"Specified root directory does not exist: {os.path.abspath(self.courses_root)}")

        index_md = "# Přehled splněných předmětů\n"
        programme_semesters_dict = {}
        for semester in os.listdir(self.courses_root):
            for programme in os.listdir(os.path.join(self.courses_root, semester)):
                # print(f"{semester} -> {programme}")
                if programme not in programme_semesters_dict:
                    programme_semesters_dict[programme] = []

                programme_semesters_dict[programme].append(semester)

        for programme, semesters in programme_semesters_dict.items():
            programme_name_no_ext = programme.rsplit(".", 1)[0]

            index_md += f'## Program {programme_name_no_ext}\n'
            for semester in semesters:
                index_md += f'- [{util.semester_id_to_str(semester)}]({os.path.join(os.path.relpath(self.courses_root, self.index_root),semester,programme_name_no_ext)})\n'

            index_md += '\n\n'

        with open(os.path.join(self.index_root, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(index_md)

    def _make_page_heading_index(self, index_columns, courses_data):
        """Create index of anchor links to given courses."""
        # {course_name} ({course_id})

        index_matrix = []
        index_rows = math.ceil(len(courses_data) / index_columns)
        [index_matrix.append([]) for _ in range(index_rows)]

        sorted_courses_data = sorted(courses_data, key=lambda item: item[0]['course_id'])
        for i, course_data in enumerate(sorted_courses_data):
            course_id = course_data[0]['course_id']
            course_name = course_data[0]['course_name']
            print(course_id)
            anchor_link = f'#{course_name.lower()}-{course_id.lower()}'.replace(' ', '-').replace('.', '')
            anchor_full = f'[{course_id}]({anchor_link})'

            cur_row = i // index_columns

            index_matrix[cur_row].append(anchor_full)

        from pprint import pprint
        pprint(index_matrix)
        md_heading = f'{"| "*index_columns}|'
        md_separator = md_heading.replace(' ', '-')
        md_content = ''

        for row in index_matrix:
            md_content += f'|{" | ".join(row)}|\n'

        md_index = f'''
{md_heading}
{md_separator}
{md_content}
        '''
        print(md_index)
        return md_index

    def _make_pages(self, index_columns=6):
        for semester_programme, semester_courses in self.data.items():
            programme_md_heading = f"# {util.semester_id_to_str(self.semester)} - předměty programu {semester_programme}"
            programme_md_tables = ""
            programme_md_footer = f'\n\n*Stav k {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}*'

            programme_md_heading_index = self._make_page_heading_index(index_columns, semester_courses.values())

            for course_id, course_data in semester_courses.items():
                md_page = self._make_md_table(semester_programme, course_data)
                programme_md_tables += md_page
                programme_md_tables += "\n"

            tgt_dir = os.path.join(self.courses_root, self.semester)
            os.makedirs(tgt_dir, exist_ok=True)
            with open(os.path.join(tgt_dir, util.sanitize_fn(semester_programme) + '.md'), 'w', encoding='utf-8') as f:
                f.write(programme_md_heading + "\n\n")
                f.write(programme_md_heading_index + "\n\n")
                f.write(programme_md_tables)
                f.write(programme_md_footer)

    def _make_md_table(self, study_programme: str, course_semester_data: List[Dict[str, Union[str, int, float]]]):
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
            row_data_separator.append("-" * 20)

            new_completed = datapoint['finished']
            new_completed_percent = datapoint['percent_finished']
            completed_delta = new_completed - previous_completed
            completed_percent_delta = new_completed_percent - previous_completed_percent
            previous_completed = new_completed
            previous_completed_percent = new_completed_percent

            row_data_compl_total.append(f'''{new_completed} ({completed_delta:+})''')
            row_data_compl_total_percent.append(
                f'''{datapoint['percent_finished']*100:.0f}% ({completed_percent_delta*100:+.0f}%)''')

        md = f"""## {course_name} ({course_id})

**Přihlášeno studentů**: {enrolled_total}

{row_headers}{"|".join(row_data_headers)}|
{row_separator}{"|".join(row_data_separator)}|
{row_completed_total}{"|".join(row_data_compl_total)}|
{row_completed_total_percent}{"|".join(row_data_compl_total_percent)}|
"""

        return md


class SurveyMiner:
    def __init__(self, data_folder='data'):
        super().__init__()
        self.data_folder = data_folder

    def update_data(self, semester, now=datetime.datetime.now()):
        old_data = self._load_semester(semester)
        courses = self._fetch_courses()
        self._add_new_course_data(courses, old_data, now.timestamp())

        fn = f'{self.data_folder}/{semester.upper()}.json'
        self._save_data(fn, old_data)

    def get_semester_data(self, semester):
        return self._load_semester(semester)

    def _add_new_course_data(self, new_data, original_data, timestamp):
        for course_data in new_data.values():
            self._merge_single_course(course_data, original_data, timestamp)

    def _load_semester(self, semester: str):
        fn = f'{self.data_folder}/{semester.upper()}.json'
        if not os.path.exists(fn):
            return {}

        with open(fn, encoding='utf-8') as f:
            data = json.load(f)

        return data

    def _parse_page(self, page: str) -> Dict:
        result = {}
        page = page.decode('utf-8')

        # Fix page first - there are mi
        # ssing opening <tr> tags
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

    def _fetch_courses(self):
        response = requests.get('https://anketa.cvut.cz/stav/stav_anketa_fit.html')
        response.raise_for_status()
        courses = self._parse_page(response.content)
        return courses

    def _save_data(self, fn, data):
        if not os.path.exists(os.path.dirname(fn)):
            os.mkdir(os.path.dirname(fn))

        with open(f"{fn}.temp", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if os.path.exists(fn):
            os.remove(fn)

        os.rename(f"{fn}.temp", fn)

    def _merge_single_course(self, new_course_data, original_data, timestamp):
        new_course_id = new_course_data['course_id']
        new_course_data['timestamp'] = timestamp

        original_course_data = self._parse_course_data(new_course_id, original_data)
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

    def _parse_course_data(self, course_id: str, data):
        study_programme = course_id.split('-', maxsplit=1)[0]
        if not data:
            return []

        try:
            course_data = data[study_programme]
            course_data = course_data[course_id]
            return course_data
        except KeyError:
            return []


def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def publish(root, temp_checkout_folder='checkouted_page'):
    if os.path.exists(temp_checkout_folder):
        shutil.rmtree(temp_checkout_folder, onerror=del_rw)

    repo = Repo.clone_from('git@github.com:melkamar/fitanketa-miner.git', temp_checkout_folder, branch='gh-pages')
    copy_tree(root, temp_checkout_folder)

    repo.git.add('--all')
    repo.index.commit("autocommit")
    repo.remote().push()


def parse_args():
    parser = argparse.ArgumentParser('Gather stats about passed courses from anketa FIT ČVUT')
    parser.add_argument('--continuous', help='Run continuously in a loop, repeat in intervals specified '
                                             'by the argument --interval.', action='store_true')
    parser.add_argument('--interval', help='Interval in minutes for repeated stats gathering.', default=15)
    return parser.parse_args()


def main():
    args = parse_args()

    while True:
        try:
            now = datetime.datetime.now()
            semester = util.get_semester(now)

            miner = SurveyMiner()
            miner.update_data(semester)
            semester_data = miner.get_semester_data(semester)

            generator = SiteGenerator('page', 'page/courses', semester_data, semester)
            generator.generate_page()

            publish('page')

        except Exception as e:
            logging.exception(e)

        if not args.continuous:
            break

        time.sleep(args.interval)


if __name__ == '__main__':
    main()
