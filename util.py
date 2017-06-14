import datetime


def get_semester(date: datetime.datetime) -> str:
    """
    Semesters are coded B161 (winter 2016/2017), B162 (summer 2016/2017) etc.

    They are obtained by comparing dates:
        January-February year X -> winter semester of year (X-1)/X
        March-September year X  -> summer semester of year (X-1)/X
        October-December year X  -> winter semester of year X/(X+1)
    :return: String representing the semester, such as B161.
    """

    now_date = datetime.datetime.now()
    year = now_date.year % 1000
    month = now_date.month

    if month in [1, 2]:
        return f"B{year-1}1"
    elif month in [3, 4, 5, 6, 7, 8, 9]:
        return f"B{year-1}2"
    elif month in [10, 11, 12]:
        return f"B{year}1"
