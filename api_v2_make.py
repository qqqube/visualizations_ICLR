import openreview
from datetime import datetime
import pytz
import argparse
from utils import _get_credentials
import os
import pandas as pd


def init_api_v2(venue_id, USERNAME, PASSWORD):
    """
    Return client for API V2
    """
    return openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net',
                                           username=USERNAME, password=PASSWORD)


def _make_submissions(client, venue_id, save_path):
    """ Create submissions table """
    
    print(f"enter api_v2_make._make_submissions save_path {save_path}")
    venue_group = client.get_group(venue_id)

    # ------ get all submissions -----
    submission_name = venue_group.content['submission_name']['value']
    # this is a list of Note objects
    submissions = client.get_all_notes(invitation=f"{venue_id}/-/{submission_name}")

    print(f"found {len(submissions)} submissions")
    records = []
    for submission in submissions:

        # ---- sanity checks ------
        assert len(submission.content["title"].keys()) == 1
        assert len(submission.content["authors"].keys()) == 1
        assert len(submission.content["authorids"].keys()) == 1
        assert len(submission.content["keywords"].keys()) == 1
        assert len(submission.content["abstract"].keys()) == 1
        assert len(submission.content["primary_area"].keys()) == 1
        if "pdf" in submission.content.keys():
            assert len(submission.content["pdf"].keys()) == 1

        record = {"id": submission.id, "number": submission.number,
                  "mdate": submission.mdate, "tmdate": submission.tmdate, # modification unix timestamps in milliseconds
                  "title": submission.content["title"]["value"], # string
                  "authors": submission.content["authors"]["value"], # list of strings
                  "authorids": submission.content["authorids"]["value"], # list of strings
                  "keywords": submission.content["keywords"]["value"], # list of strings
                  "abstract": submission.content["abstract"]["value"], # string
                  "primary_area": submission.content["primary_area"]["value"], # string
                  "pdf": submission.content["pdf"]["value"] if "pdf" in submission.content.keys() else "" # string (path to pdf file, could be empty string for authors who withdrew before the deadline)
                  }
        
        records.append(record)
    
    print(f"found {len(records)} records")
    df = pd.DataFrame.from_records(records)

    # ------ add decision outcome (withdrawn/accepted/desk_rejected/rejected) ----
    accepted_submissions = client.get_all_notes(content={'venueid': venue_id})
    accepted_id_lst = [sub.id for sub in accepted_submissions]
    print(f"found {len(accepted_submissions)} accepted submissions")

    withdrawn_id = venue_group.content['withdrawn_venue_id']['value']
    withdrawn_submissions = client.get_all_notes(content={'venueid': withdrawn_id})
    withdrawn_id_lst = [sub.id for sub in withdrawn_submissions]
    print(f"found {len(withdrawn_submissions)} withdrawn submissions")

    desk_rejected_venue_id = venue_group.content['desk_rejected_venue_id']['value']
    desk_rejected_submissions = client.get_all_notes(content={'venueid': desk_rejected_venue_id})
    desk_rejected_id_lst = [sub.id for sub in desk_rejected_submissions]
    print(f"found {len(desk_rejected_submissions)} desk rejected submissions")

    assert len(set(accepted_id_lst).intersection(set(withdrawn_id_lst))) == 0
    assert len(set(accepted_id_lst).intersection(set(desk_rejected_id_lst))) == 0
    assert len(set(withdrawn_id_lst).intersection(set(desk_rejected_id_lst))) == 0
    
    def categorize(submission_id):
        """
        Return one of withdrawn/accepted/desk_rejected/rejected
        """
        if submission_id in accepted_id_lst:
            return "Accepted"
        elif submission_id in withdrawn_id_lst:
            return "Withdrawn"
        elif submission_id in desk_rejected_id_lst:
            return "Desk_Rejected"
        return "Rejected"
    
    df["outcome"] = df.apply(func=lambda row: categorize(row["id"]), axis=1)
    df.to_csv(save_path, index=False)


def _make_discussions(client, venue_id, save_path):
    """ Create discussions table """


if __name__ == "__main__":

    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_path", type=str, default="../credentials.ini") # path to config that contains username and password
    parser.add_argument("--venue_id", type=str)
    parser.add_argument("--save_dir", type=str) # path to directory to save csv files in
    args = parser.parse_args()

    USERNAME, PASSWORD = _get_credentials(args.credentials_path)
    client = init_api_v2(args.venue_id, USERNAME, PASSWORD)

    # ------ create submissions.csv -------
    _make_submissions(client, args.venue_id, os.path.join(args.save_dir, "submissions.csv"))

    # ------ create discussions.csv ------
    _make_discussions(client, args.venue_id, os.path.join(args.save_dir, "discussions.csv"))
