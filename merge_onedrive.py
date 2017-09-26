"""
This is only intended as a one-time use to migrate data from
https://onedrive.live.com/view.aspx?resid=1D94BDD6FAAB6007!14349&app=Excel&authkey=!APuzdricEjAteac
to this tool.
"""
import csv
import datetime
import json
import os

SEMESTER_TIMESTAMP = {
    'B091': datetime.datetime.strptime("2009.01.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B092': datetime.datetime.strptime("2009.01.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B101': datetime.datetime.strptime("2010.01.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B102': datetime.datetime.strptime("2010.06.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B111': datetime.datetime.strptime("2011.01.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B112': datetime.datetime.strptime("2011.06.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B121': datetime.datetime.strptime("2012.01.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
    'B122': datetime.datetime.strptime("2012.06.26 12:00", "%Y.%m.%d %H:%M").timestamp(),
}

INDICES = {
    'MI': {
        'B101': {
            'enrolled': 35,
            'finished': 36
        },
        'B102': {
            'enrolled': 31,
            'finished': 32
        },
        'B111': {
            'enrolled': 27,
            'finished': 28
        },
        'B112': {
            'enrolled': 23,
            'finished': 24
        },
        'B121': {
            'enrolled': 19,
            'finished': 20
        },
        'B122': {
            'enrolled': 15,
            'finished': 16
        },
    },
    'BI': {
        'B091': {
            'enrolled': 51,
            'finished': 52
        },
        'B092': {
            'enrolled': 47,
            'finished': 48
        },
        'B101': {
            'enrolled': 43,
            'finished': 44
        },
        'B102': {
            'enrolled': 39,
            'finished': 40
        },
        'B111': {
            'enrolled': 35,
            'finished': 36
        },
        'B112': {
            'enrolled': 31,
            'finished': 32
        },
        'B121': {
            'enrolled': 27,
            'finished': 28
        },
        'B122': {
            'enrolled': 23,
            'finished': 24
        },

    }
}

FILENAMES = {
    'MI': 'fitpruchod.csv',
    'BI': 'fitpruchod-bakalar.csv',
}


def parse_programme_dict(programme_id, result_dict):
    """
    Create dictionary:
    {
      semester_id: {
        MI: {
          course: {},
          course: {}
        },
        BI: {
          course: {},
          course: {}
        {
      }
    }
    :param programme_id:
    :param result_dict:
    :return:
    """

    csv_fn = FILENAMES[programme_id]
    with open(csv_fn) as csvf:
        csv_reader = csv.reader(csvf, delimiter=';')

        for row in csv_reader:
            course_id = row[0]
            course_name = row[1]
            if not course_id or course_id == 'SUMA':
                continue  # Skip empty course codes

            for semester, _indices in INDICES[programme_id].items():
                if semester not in result_dict:
                    result_dict[semester] = {}
                if programme_id not in result_dict[semester]:
                    result_dict[semester][programme_id] = {}

                index_enrolled = _indices['enrolled']
                index_finished = _indices['finished']

                enrolled = row[index_enrolled]
                finished = row[index_finished]

                if not enrolled or not finished:
                    continue  # Skip semesters where course did not have any people

                result_dict[semester][programme_id][course_id] = []
                result_dict[semester][programme_id][course_id].append({
                    'department': 0,
                    'course_id': course_id,
                    'course_name': course_name,
                    'enrolled': enrolled,
                    'finished': finished,
                    'submitted_survey': 0,
                    'percent_finished': int(finished) / int(enrolled),
                    'timestamp': SEMESTER_TIMESTAMP[semester],
                })


def save_dict_to_separate_courses(data_dict, data_root):
    """
    Save dictionary in format from parse_programme_dict() into files, one file per semester.
    :param data_dict:
    :param data_root: Folder where data JSON files lie.
    :return:
    """
    if not os.path.exists(data_root):
        os.makedirs(data_root)

    for semester_id, semester_data in data_dict.items():
        fn = os.path.join(data_root, semester_id + '.json')
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(semester_data, f, ensure_ascii=False, indent=2)


def merge_data():
    result_dict = {}
    parse_programme_dict('BI', result_dict)
    parse_programme_dict('MI', result_dict)

    save_dict_to_separate_courses(result_dict, 'datatest')

    import pprint
    pprint.pprint(result_dict)


def create_pages():
    from minefit import SiteGenerator, SurveyMiner
    miner = SurveyMiner()

    for semester_id in SEMESTER_TIMESTAMP:
        data = miner.get_semester_data(semester_id)
        gen = SiteGenerator('pagetest', 'pagetest/courses', data, semester_id, 'data')
        gen.generate_page()


def main():
    # merge_data()

    create_pages()


if __name__ == '__main__':
    main()
