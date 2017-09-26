# fitanketa-miner
Script for mining the FIT CTU course pass percentages

## Usage
When run, the script connects to https://anketa.cvut.cz/stav/stav_anketa_fit.html, parses its contents and appends the 
information to the `courses.json` file. The file has following structure:

```json
{
  "1496326146": {
    "BI-ACM2": {
      "department": 18101,
      "course_id": "BI-ACM2",
      "course_name": "Programovací praktika",
      "enrolled": 36,
      "finished": 35,
      "submitted_survey": 0,
      "percent_finished": 0.9722222222222222
    },
    "BI-AG2": {
      "department": 18101,
      "course_id": "BI-AG2",
      "course_name": "Algoritmy a grafy 2",
      "enrolled": 82,
      "finished": 10,
      "submitted_survey": 0,
      "percent_finished": 0.12195121951219512
    }
  },
  "1496326158":{
    
  }
}
```

The keys in the dict are UTC timestamps of the associated data. The rest is pretty self-explanatory.

## How does it work

Mine https://anketa.cvut.cz/stav/stav_anketa_fit.html for data about
how many students have finished what courses.

Save this data in a per-day basis, in JSON (because there won't be
much data and JSON is real easy in Python, mkay?)
Only store data for courses where there has been a change from the last
state. So if every day one more person passes the course, there will
be a datapoint every day. If, on the other hand, all the people
passing the course get added into the system at once, there will be a
single datapoint for the whole semester.