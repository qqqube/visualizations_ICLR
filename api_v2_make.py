import openreview
from datetime import datetime
import pytz
import argparse
from utils import _get_credentials
import os
import pandas as pd


def init_api_v2(USERNAME, PASSWORD):
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


def _make_discussions(client, venue_id, save_dir):
    """ Create official reviews and official comments tables """

    print(f"enter api_v2_make._make_discussion save_path {save_dir}")
    venue_group = client.get_group(venue_id)

    # ----- get all submissions & replies to submissions -----------
    submission_name = venue_group.content['submission_name']['value']
    submissions = client.get_all_notes(invitation=f'{venue_id}/-/{submission_name}', details='replies')

    # --- make official review table ---------
    review_name = venue_group.content['review_name']['value'] # official review name
    review_records = []
    for submission in submissions:
        for reply in submission.details["replies"]:
            # reply is an official review
            if f'{venue_id}/{submission_name}{submission.number}/-/{review_name}' in reply['invitations']:
                record = {"id": reply["id"], # str
                          "replyto": reply["replyto"], # str containing id of submission
                          "tcdate" : reply["tcdate"], # unix timestamp in milliseconds for true creation date
                          "tmdate": reply["tmdate"], # unix timestamp in milliseconds for true modification date
                          
                          # ---- content ------
                          "summary": reply["content"]["summary"]["value"], # str
                          "soundness": reply["content"]["soundness"]["value"], # int
                          "presentation": reply["content"]["presentation"]["value"], #int
                          "contribution": reply["content"]["contribution"]["value"], #int
                          "strengths": reply["content"]["strengths"]["value"], # str
                          "weaknesses": reply["content"]["weaknesses"]["value"], # str
                          "questions": reply["content"]["questions"]["value"], # str
                          "rating": reply["content"]["rating"]["value"], # int 
                          "confidence": reply["content"]["confidence"] #int
                          }
                review_records.append(record)
    df = pd.DataFrame.from_records(review_records)
    print(f"found {df.shape[0]} reviews")
    df.to_csv(os.path.join(save_dir, "official_reviews.csv"), escapechar="\\", index=False)
    print("created official_reviews.csv")

    # ---- make official comments table (author & reviewer responses to official reviews) --------
    comment_records = []
    for submission in submissions:
        for reply in submission.details["replies"]:
            # reply is an official comment
            if reply['invitations'][0].endswith('Official_Comment'):
                
                # response by who
                by_author = any('Authors' in mem for mem in reply['signatures'])
                by_reviewer = any("Reviewer_" in mem for mem in reply["signatures"])
                if not any([by_author, by_reviewer]):
                    continue

                record = {"id": reply["id"],
                          "replyto": reply["replyto"],
                          "tcdate": reply["tcdate"], # unix timestamp in milliseconds for true creation date
                          "tmdate": reply["tmdate"], # unix timestamp in milliseconds for true modification date
                          "writer": "Authors" if by_author else "Reviewer",

                          # ------ content ---------
                          "title": reply["content"]["title"]["value"] if "title" in reply["content"].keys() else "", # str
                          "comment": reply["content"]["comment"]["value"], # str
                          }
                comment_records.append(record)
    df = pd.DataFrame.from_records(comment_records)
    print(f"found {df.shape[0]} official comments")
    df.to_csv(os.path.join(save_dir, "official_comments.csv"), escapechar="\\", index=False)
    print("created official_comments.csv")


if __name__ == "__main__":

    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_path", type=str, default="../credentials.ini") # path to config that contains username and password
    parser.add_argument("--venue_id", type=str)
    parser.add_argument("--save_dir", type=str) # path to directory to save csv files in
    args = parser.parse_args()

    USERNAME, PASSWORD = _get_credentials(args.credentials_path)
    client = init_api_v2(USERNAME, PASSWORD)

    # ------ create submissions.csv -------
    #_make_submissions(client, args.venue_id, os.path.join(args.save_dir, "submissions.csv"))

    # ------ create official_reviews.csv and official_comments.csv ------
    _make_discussions(client, args.venue_id, args.save_dir)
