#!/bin/usr/env python3

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
    """
    Class for generating the markdown-syntaxed site from course data.
    """

    def __init__(self, index_root, courses_root, data_root):
        """

        :param index_root: Path to the root folder of the page, where the index should be created.
        :param courses_root: Path to the root of courses pages, where "[semester_code]/[BI.md]" structure for each
                             programme will be created.
        :param data:
        :param semester:
        :param data_root: Path to the root folder with JSON data folders. Used to create long-term pages.
        """
        super().__init__()
        self.index_root = index_root
        self.courses_root = courses_root
        self.data_root = data_root

    def generate_page(self):
        """
        Generate the whole web structure.

        :return: None, everything is saved under index_root/** .
        """
        for semester_datafile in os.listdir(self.data_root):
            self._make_pages(os.path.splitext(semester_datafile)[0], 6)

        self._make_longterm_pages("data")
        self._make_index()

    def _make_index(self):
        """
        Create the index page pointing to all the study programmes and all semesters.
        Save this page as index_root/README.md .

        :return: None.
        """
        if not os.path.exists(self.courses_root):
            raise ValueError(f"Specified root directory does not exist: {os.path.abspath(self.courses_root)}")

        index_md = ""

        longterm_folder = os.path.join(self.index_root, "longterm")
        index_md += "# Celková průchodnost předmětů\n\n"
        longterm_programmes = os.listdir(longterm_folder)
        for programme_fn in longterm_programmes:
            programme_id = os.path.splitext(programme_fn)[0]
            index_md += f'- [Předměty programu {programme_id}](longterm/{programme_id})\n'
        index_md += '\n\n'

        # Create detailed index - point to separate years
        index_md += "# Detailní přehled průchodů předměty\n"
        programme_semesters_dict = {}
        for semester in sorted(os.listdir(self.courses_root)):
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

    @staticmethod
    def _make_page_heading_index(index_columns, courses_data):
        """Create index of anchor links to given courses. One index per study programme.
        Courses data is list of lists of courses dicts:
        courses_data = [
            [
             {course_id:A, finished:...},
             {course_id:A, finished:...},
            ],
            [
             {course_id:B, finished:...},
             {course_id:B, finished:...},
            ],
            ...
        ]
        """
        # {course_name} ({course_id})
        import pprint
        pprint.pprint(courses_data)
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

    def _make_longterm_pages(self, data_root, index_columns=6):
        """
        Make a page for every programme. Save the pages under
        the index_root/longterm folder.

        Read every json datafile in data_root and create one table per course, containing the last passing percentage
        per year.

        First a dictionary will be created:
        {
            'BI':{
                'course_id': [
                    {course_id:..., department:..., enrolled: ..., ...},
                    {course_id:..., department:..., enrolled: ..., ...},
                ],
                'course_id2':[
                    ...
                ]
            },
            'MI':{
            }
        }

        This will be then used to generate one page per study programme.

        :param data_root: Path to the folder containing JSON data files.
        :param index_columns:
        :return:
        """

        def _build_programme_page(programme_id, programme_data):

            programme_md_heading = f"# Předměty programu {programme_id}\n\n"
            programme_md_footer = f'\n\n*Stav k {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}*'

            programme_md_heading_index = self._make_page_heading_index(index_columns, programme_data.values())

            root_folder = os.path.join(self.index_root, 'longterm')
            os.makedirs(root_folder, exist_ok=True)

            with open(os.path.join(root_folder, programme_id + ".md"), 'w', encoding='utf-8') as f:
                f.write(programme_md_heading)
                f.write(programme_md_heading_index)
                f.write('\n')

                for course_id, course_data_list in sorted(programme_data.items()):
                    sorted_list = sorted(course_data_list, key=lambda course_dict: course_dict['timestamp'])
                    longterm_dict[programme_id][course_id] = sorted_list

                    md_table = self._make_md_table(sorted_list, show_delta=False, show_students_enrolled=False,
                                                   show_students_enrolled_inline=True)

                    f.write(md_table + "\n\n")

                    print(md_table)

                f.write(programme_md_footer)

        longterm_dict = {}

        data_files = os.listdir(data_root)
        for datafile in data_files:
            with open(os.path.join(data_root, datafile), encoding='utf-8') as f:
                data_dict = json.load(f)

                for programme_id, programme_data in data_dict.items():
                    if programme_id not in longterm_dict:
                        longterm_dict[programme_id] = {}

                    for course_id, course_data_list in programme_data.items():
                        last_course_data = course_data_list[-1]
                        if course_id not in longterm_dict[programme_id]:
                            longterm_dict[programme_id][course_id] = []

                        longterm_dict[programme_id][course_id].append(last_course_data)

        # Now go through the dictionary again and sort the lists using timetables as keys, just to be sure
        # Yeah, slow, but whatever, there wont be much data
        for programme_id, programme_data in longterm_dict.items():
            _build_programme_page(programme_id, programme_data)

        # import pprint
        # pprint.pprint(longterm_dict)
        print()

    def _make_pages(self, semester, index_columns=6):
        """
        Make a page for every programme in the current semester. Save the pages under
        the courses_root/semester_id folder.

        :param index_columns: Number of columns the index of the page should have.
        :return: None.
        """
        data = SurveyMiner().get_semester_data(semester)
        for semester_programme, semester_courses in data.items():
            programme_md_heading = f"# {util.semester_id_to_str(semester)} - předměty programu {semester_programme}"
            programme_md_tables = ""
            programme_md_footer = f'\n\n*Stav k {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}*'

            programme_md_heading_index = self._make_page_heading_index(index_columns, semester_courses.values())

            for course_id, course_data in semester_courses.items():
                md_page = self._make_md_table(course_data)
                programme_md_tables += md_page
                programme_md_tables += "\n"

            tgt_dir = os.path.join(self.courses_root, semester)
            os.makedirs(tgt_dir, exist_ok=True)
            with open(os.path.join(tgt_dir, util.sanitize_fn(semester_programme) + '.md'), 'w', encoding='utf-8') as f:
                f.write(programme_md_heading + "\n\n")
                f.write(programme_md_heading_index + "\n\n")
                f.write(programme_md_tables)
                f.write(programme_md_footer)

    def _make_md_table(self, course_semester_data: List[Dict[str, Union[str, int, float]]], show_delta=True,
                       show_students_enrolled=True, show_students_enrolled_inline=False):
        """
        Make markdown table from data of a single semester-course.

        :param study_programme:
        :param course_semester_data: List of datapoints of the course, example:
                                     [
                                         {course_id:..., department:..., enrolled: ..., ...},
                                         {course_id:..., department:..., enrolled: ..., ...},
                                     ]
        :return: Markdown-syntax table.
        """
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

            new_completed = int(datapoint['finished'])
            new_completed_percent = float(datapoint['percent_finished'])
            completed_delta = new_completed - previous_completed
            completed_percent_delta = new_completed_percent - previous_completed_percent
            previous_completed = new_completed
            previous_completed_percent = new_completed_percent

            if show_delta:
                row_data_compl_total.append(f'''{new_completed} ({completed_delta:+})''')
                row_data_compl_total_percent.append(
                    f'''{datapoint['percent_finished']*100:.0f}% ({completed_percent_delta*100:+.0f}%)''')
            else:
                if show_students_enrolled_inline:
                    row_data_compl_total.append(f'''{new_completed}/{datapoint['enrolled']}''')
                    row_data_compl_total_percent.append(
                        f'''{datapoint['percent_finished']*100:.0f}%''')
                else:
                    row_data_compl_total.append(f'''{new_completed}''')
                    row_data_compl_total_percent.append(
                        f'''{datapoint['percent_finished']*100:.0f}%''')

        md = f"## {course_name} ({course_id})\n\n"
        if show_students_enrolled:
            md += f"**Přihlášeno studentů**: {enrolled_total}\n\n"

        md += f"""{row_headers}{"|".join(row_data_headers)}|
{row_separator}{"|".join(row_data_separator)}|
{row_completed_total}{"|".join(row_data_compl_total)}|
{row_completed_total_percent}{"|".join(row_data_compl_total_percent)}|
"""
        return md


class SurveyMiner:
    """
    Class for parsing and merging course completion data.
    """

    def __init__(self, data_folder='data'):
        """

        :param data_folder: Path to folder where datafiles for semesters are present.
        """
        super().__init__()
        self.data_folder = data_folder

    def update_data(self, semester, now=datetime.datetime.now(), courses_data=None):
        """
        Update an existing semester data file, or create a new one if none exists.

        :param semester: Semester-code (e.g. B162) for which to process the data. Use util.get_semester(now) to get
                         the semester code.
        :param now: Time with which the data will be timestamped.
        :param courses_data: If None, data is fetched from the anketa. Otherwise, this data dict is used. Its format
                             is described in method SurveyMiner#_parse_page().
        :return: None.
        """
        old_data = self._load_semester(semester)
        if courses_data is None:
            courses = self._fetch_courses()
        else:
            courses = courses_data

        self._add_new_course_data(courses, old_data, now.timestamp())

        fn = f'{self.data_folder}/{semester.upper()}.json'
        self._save_data(fn, old_data)

    def get_semester_data(self, semester):
        """
        Load existing datafile for the given semester and return it back as a dict.

        :param semester: Semester code (e.g. B162). Use util.get_semester(now) to get the semester code.
        :return: Semester data dictionary, its format described in method _merge_single_course().
        """
        return self._load_semester(semester)

    def _add_new_course_data(self, new_data, original_data, timestamp):
        """
        Merge existing and new data for a semester of courses.

        :param new_data: Dictionary containing the new data.
        :param original_data: Dictionary containing the old data.
        :param timestamp: Timestamp at which to save the new data.
        :return: None.
        """
        for course_data in new_data.values():
            self._merge_single_course(course_data, original_data, timestamp)

    # noinspection PyMethodMayBeStatic
    def _load_semester(self, semester: str):
        """
        Load semester data from a file into a dictionary. The format of this dictionary is described in
        method _merge_single_course().

        :param semester: Semester code (e.g. B162). Use util.get_semester(now) to get the semester code.
        :return: Dictionary of the saved course data.
        """
        fn = f'{self.data_folder}/{semester.upper()}.json'
        if not os.path.exists(fn):
            return {}

        with open(fn, encoding='utf-8') as f:
            data = json.load(f)

        return data

    @staticmethod
    def _parse_page(page: str) -> Dict:
        """
        Parse anketa page to get a dictionary describing the courses data.

        The dictionary has the following structure::

            {
                'course_code': {
                    'department': id of the course's department (int),
                    'course_id': id of the course (e.g. MI-PDP),
                    'course_name': human readable name of the course (e.g. Paralelní a distribuované programování),
                    'enrolled': number of students enrolled in the course for this semester,
                    'finished': number of students that have finished the course in this semester,
                    'submitted_survey': number of students that have filled in the survey (anketa),
                    'percent_finished': percentage of students that have finished the course
                },
                'course_code_B': {
                    ...
                }, ...
            }

        :param page: Raw HTML of the page to process.
        :return: Dictionary of courses data.
        """
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
        """
        Get the newest data about courses from the anketa webpage. Parse them into a dictionary.

        :return: Dictionary described in method SurveyMiner#parse_page()
        """
        response = requests.get('https://anketa.cvut.cz/stav/stav_anketa_fit.html')
        response.raise_for_status()
        courses = self._parse_page(response.content)
        return courses

    @staticmethod
    def _save_data(fn, data):
        """
        Save data (dict) into a json file.

        :param fn: Target filename.
        :param data: Dictinary of courses data.
        :return: None.
        """
        if not os.path.exists(os.path.dirname(fn)):
            os.mkdir(os.path.dirname(fn))

        with open(f"{fn}.temp", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if os.path.exists(fn):
            os.remove(fn)

        os.rename(f"{fn}.temp", fn)

    def _merge_single_course(self, new_course_data, original_data, timestamp):
        """
        Merge past and new data for a single course in a single semester.

        :param new_course_data: Dictionary with the course's data:
                                {'department': ...,
                                 'course_id': ...,
                                 'course_name': ...,
                                 'enrolled': ...,
                                 'finished': ...,
                                 'submitted_survey': ...,
                                 'percent_finished': ...}
        :param original_data: Full dictionary of the original data, structured as follows:
                                Dict[study_programme, Dict[course_id, List[course_data]]]

                                {
                                    'study_programme (e.g. BI, MI ...)': {
                                        'course_id (e.g. MI-PDP': [
                                            {course_data (see new_course_data format)},
                                            {course_data2 (see new_course_data format)},
                                            ...
                                        ],
                                        'course_id_2 (e.g. MI-MPI': [
                                            {course_data (see new_course_data format)},
                                            {course_data2 (see new_course_data format)},
                                            ...
                                        ],
                                    },
                                    'study_programme_2': {
                                        ...
                                    }
                                }
        :param timestamp: Timestamp at which to save the new data.
        :return: None. The method will change the original data dictionary in-place.
        """
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

    @staticmethod
    def _parse_course_data(course_id: str, data):
        """
        Get list of datapoints of a course from the whole dataset.

        :param course_id: ID of the course, e.g. MI-PDP.
        :param data: Dictionary of the whole semester's data. See method _merge_single_course() for details.
        :return: List of course data dictionaries. See method _merge_single_course() for details.
        """
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
    """
    Publish a gitpage to github by pushing the changes to gh-pages branch of this repo.

    :param root: Path to the root of the page. The root should contain "README.md" and "courses/semester_code" folders.
    :param temp_checkout_folder: Temporary folder where to checkout current data.
    :return: None.
    """
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

            generator = SiteGenerator('page', 'page/courses', 'data')
            generator.generate_page()

            publish('page')

        except Exception as e:
            logging.exception(e)

        if not args.continuous:
            break

        time.sleep(int(args.interval))


if __name__ == '__main__':
    main()
