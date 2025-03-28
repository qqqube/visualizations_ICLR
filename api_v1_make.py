import openreview
from datetime import datetime
import pytz
import argparse
from utils import _get_credentials
import os
import pandas as pd
from tqdm import tqdm


BLIND_SUBMISION = {2017: "ICLR.cc/2017/conference/-/submission", 
                   2018: "ICLR.cc/2018/Conference/-/Blind_Submission", 
                   2019: "ICLR.cc/2019/Conference/-/Blind_Submission", 
                   2020: "ICLR.cc/2020/Conference/-/Blind_Submission", 
                   2021: "ICLR.cc/2021/Conference/-/Blind_Submission",
                   2022: "ICLR.cc/2022/Conference/-/Blind_Submission",
                   2023: "ICLR.cc/2023/Conference/-/Blind_Submission"}

WITHDRAWN_SUBMISSION = {2017: "ICLR.cc/2017/Conference/-/Withdrawn_Submission", 
                        2018: "ICLR.cc/2018/Conference/-/Withdrawn_Submission", 
                        2019: "ICLR.cc/2019/Conference/-/Withdrawn_Submission", 
                        2020: "ICLR.cc/2020/Conference/-/Withdrawn_Submission", 
                        2021: "ICLR.cc/2021/Conference/-/Withdrawn_Submission",
                        2022: "ICLR.cc/2022/Conference/-/Withdrawn_Submission",
                        2023: "ICLR.cc/2023/Conference/-/Withdrawn_Submission"}

DESK_REJECTED_SUBMISSION = {2017: "ICLR.cc/2017/Conference/-/Desk_Rejected_Submission", 
                            2018: "ICLR.cc/2018/Conference/-/Desk_Rejected_Submission", 
                            2019: "ICLR.cc/2019/Conference/-/Desk_Rejected_Submission", 
                            2020: "ICLR.cc/2020/Conference/-/Desk_Rejected_Submission", 
                            2021: "ICLR.cc/2021/Conference/-/Desk_Rejected_Submission",
                            2022: "ICLR.cc/2022/Conference/-/Desk_Rejected_Submission",
                            2023: "ICLR.cc/2023/Conference/-/Desk_Rejected_Submission"}

OFFICIAL_REVIEWS = {2017: "ICLR.cc/2017/conference/-/paper%s/official/review", 
                    2018: "ICLR.cc/2018/Conference/-/Paper%s/Official_Review", 
                    2019: "ICLR.cc/2019/Conference/-/Paper%s/Official_Review", 
                    2020: "ICLR.cc/2020/Conference/Paper%s/-/Official_Review",
                    2021: "ICLR.cc/2021/Conference/Paper%s/-/Official_Review",
                    2022: "ICLR.cc/2022/Conference/Paper%s/-/Official_Review",
                    2023: "ICLR.cc/2023/Conference/Paper%s/-/Official_Review"}

OFFICIAL_COMMENTS = {2017: "ICLR.cc/2017/conference/-/paper%s/public/comment",
                     2018: "ICLR.cc/2018/Conference/-/Paper%s/Official_Comment",
                     2019: "ICLR.cc/2019/Conference/-/Paper%s/Official_Comment",
                     2020: "ICLR.cc/2020/Conference/Paper%s/-/Official_Comment",
                     2021: "ICLR.cc/2021/Conference/Paper%s/-/Official_Comment",
                     2022: "ICLR.cc/2022/Conference/Paper%s/-/Official_Comment",
                     2023: "ICLR.cc/2023/Conference/Paper%s/-/Official_Comment"}


ACCEPTED = "Accepted"
REJECTED = "Rejected"

def _outcome_2020(note, client):
    invitation = f"ICLR.cc/2020/Conference/Paper{note.number}/-/Decision"
    decision_notes = [item for item in openreview.tools.iterget_notes(client, invitation=invitation)]
    assert len(decision_notes) == 1
    mapping = {
               "Accept (Poster)": ACCEPTED,
               "Accept (Spotlight)": ACCEPTED,
               "Accept (Talk)": ACCEPTED,
               "Reject": REJECTED
               }
    return mapping[decision_notes[0].content["decision"]]

def _outcome_2019(note, client):
    invitation = f"ICLR.cc/2019/Conference/-/Paper{note.number}/Meta_Review"
    decision_notes = [item for item in openreview.tools.iterget_notes(client, invitation=invitation)]
    assert len(decision_notes) == 1
    mapping = {
               "Accept (Poster)": ACCEPTED,
               "Accept (Oral)": ACCEPTED,
               "Reject": REJECTED
               }
    return mapping[decision_notes[0].content["recommendation"]]

def _outcome_2017(note, client):
    invitation = f"ICLR.cc/2017/conference/-/paper{note.number}/acceptance"
    decision_notes = [item for item in openreview.tools.iterget_notes(client, invitation=invitation)]
    assert len(decision_notes) == 1
    mapping = {"ICLR 2017 Poster": ACCEPTED,
               "ICLR 2017 Oral": ACCEPTED,
                "Submitted to ICLR 2017": REJECTED, 
                "ICLR 2017 Invite to Workshop": REJECTED}
    return mapping[decision_notes[0].content['decision']]

DECISION_MAPPING = {2023: lambda note, _ : {'ICLR 2023 notable top 25%': ACCEPTED,
                                            'ICLR 2023 notable top 5%': ACCEPTED,
                                            'ICLR 2023 poster': ACCEPTED,
                                            'Submitted to ICLR 2023': REJECTED}[note.content["venue"]],
                    2022: lambda note, _ : {'ICLR 2022 Oral': ACCEPTED,
                                            'ICLR 2022 Poster': ACCEPTED,
                                            'ICLR 2022 Spotlight': ACCEPTED,
                                            'ICLR 2022 Submitted': REJECTED}[note.content["venue"]],
                    2021: lambda note, _ : REJECTED if "venue" not in note.content.keys() else ACCEPTED,
                    2020: _outcome_2020,
                    2019: _outcome_2019,
                    2018: lambda note, client : "",
                    2017: lambda note, _ : {"ICLR 2017 Poster": ACCEPTED,
                                            "ICLR 2017 Oral": ACCEPTED,
                                            "Submitted to ICLR 2017": REJECTED, 
                                            "ICLR 2017 Invite to Workshop": REJECTED}[note.content["venue"]],
                    }


def init_api_v1(USERNAME, PASSWORD):
    """
    Return client for API V1
    """
    return openreview.Client(baseurl='https://api.openreview.net',
                             username=USERNAME, password=PASSWORD)


def _make_submissions(client, venue_year, save_path):
    """ Create submissions table """
    
    print(f"enter api_v1_make._make_submissions save_path {save_path}")

    records = []
    # ------ get all blind submissions -----
    blind_submissions = [note for note in openreview.tools.iterget_notes(client, 
                                                                         invitation=BLIND_SUBMISION[venue_year])]
    if venue_year == 2018:
        mapping = {'Accept (Oral)': ACCEPTED,
                   'Accept (Poster)': ACCEPTED,
                   'Invite to Workshop Track': REJECTED,
                   'Reject': REJECTED}
        decision_notes = [note for note in openreview.tools.iterget_notes(client, invitation="ICLR.cc/2018/Conference/-/Acceptance_Decision")]
        decision_notes = {note.replyto: mapping[note.content["decision"]] for note in decision_notes}
    
    for submission in tqdm(blind_submissions):
        record = {"id": submission.id, "number": submission.number,
                  "mdate": submission.mdate, "tmdate": submission.tmdate, # modification unix timestamps in milliseconds
                  "title": submission.content["title"], # string
                  "authors": submission.content["authors"], # list of strings
                  "authorids": submission.content["authorids"] if "authorids" in submission.content.keys() else submission.content["author_emails"], # list of strings or just string
                  "keywords": submission.content["keywords"], # list of strings
                  "abstract": submission.content["abstract"], # string
                  "pdf": submission.content["pdf"], # string
                  "outcome": DECISION_MAPPING[venue_year](submission, client), # string
                  }
        if venue_year == 2018:
            if submission.id not in decision_notes.keys():
                if "withdrawal" in submission.content.keys() and submission.content["withdrawal"] == "Confirmed":
                    record["outcome"] = "Withdrawn"
                else:
                    continue
            else:
                record["outcome"] = decision_notes[submission.id]
        
        records.append(record)
    
    # -------- get all withdrawn submissions -----
    withdrawn_submissions = [note for note in openreview.tools.iterget_notes(client,
                                                                             invitation=WITHDRAWN_SUBMISSION[venue_year])]
    for submission in withdrawn_submissions:
        record = {"id": submission.id, "number": submission.number,
                  "mdate": submission.mdate, "tmdate": submission.tmdate, # modification unix timestamps in milliseconds
                  "title": submission.content["title"], # string
                  "authors": submission.content["authors"], # list of strings
                  "authorids": submission.content["authorids"], # list of strings
                  "keywords": submission.content["keywords"], # list of strings
                  "abstract": submission.content["abstract"], # string
                  "pdf": submission.content["pdf"], # string
                  "outcome": "Withdrawn", # string
                  }
        records.append(record)
    # -------- get all desk rejected submissions ------
    desk_rejected_submissions = [note for note in openreview.tools.iterget_notes(client, 
                                                                                 invitation=DESK_REJECTED_SUBMISSION[venue_year])]
    for submission in desk_rejected_submissions:
        record = {"id": submission.id, "number": submission.number,
                  "mdate": submission.mdate, "tmdate": submission.tmdate, # modification unix timestamps in milliseconds
                  "title": submission.content["title"], # string
                  "authors": submission.content["authors"], # list of strings
                  "authorids": submission.content["authorids"], # list of strings
                  "keywords": submission.content["keywords"], # list of strings
                  "abstract": submission.content["abstract"], # string
                  "pdf": submission.content["pdf"], # string
                  "outcome": "Desk_Rejected", # string
                  }
        records.append(record)

    print(f"found {len(records)} records")
    df = pd.DataFrame.from_records(records)
    try:
        df.to_csv(save_path, index=False)
    except Exception:
        df.to_csv(save_path, escapechar="\\", index=False)


def _make_reviews(client, venue_year):
    """ Create official_reviews.csv """

    print(f"creating {venue_year}/official_reviews.csv")
    submissions_path = os.path.join(str(venue_year), "submissions.csv")
    submissions = pd.read_csv(submissions_path)

    review_records = []
    for _, submission in tqdm(submissions.iterrows()):
        invitation = OFFICIAL_REVIEWS[venue_year] % submission["number"]
        reviews = openreview.tools.iterget_notes(client,
                                                 invitation=invitation)
        for review in reviews:
            if venue_year in [2017, 2018, 2019, 2021]:
                record = {"id": review.id, #str
                        "replyto": review.replyto, # id of submission (str)
                        "tcdate": review.tcdate,
                        "tmdate": review.tmdate,
                        
                        # ------ content -------
                        "title": review.content["title"],
                        "rating": review.content["rating"],
                        "review": review.content["review"],
                        "confidence": review.content["confidence"] if "confidence" in review.content.keys() else "",
                        }
            elif venue_year == 2020:
                record = {"id": review.id, #str
                          "replyto": review.replyto, # id of submission (str)
                          "tcdate": review.tcdate,
                          "tmdate": review.tmdate,
                        
                        # ------ content -------
                        "title": review.content["title"],
                        "rating": review.content["rating"],
                        "review": review.content["review"],
                        "experience_assessment": review.content["experience_assessment"],
                        "review_assessment:_thoroughness_in_paper_reading": review.content["review_assessment:_thoroughness_in_paper_reading"],
                        "review_assessment:_checking_correctness_of_experiments": review.content["review_assessment:_checking_correctness_of_experiments"],
                        "review_assessment:_checking_correctness_of_derivations_and_theory": review.content["review_assessment:_checking_correctness_of_derivations_and_theory"],
                        }
            elif venue_year == 2022:
                record = {"id": review.id, #str
                          "replyto": review.replyto, # id of submission (str)
                          "tcdate": review.tcdate,
                          "tmdate": review.tmdate,
                        
                        # ------ content -------
                        "summary_of_the_paper": review.content["summary_of_the_paper"],
                        "main_review": review.content["main_review"],
                        "summary_of_the_review": review.content["summary_of_the_review"],
                        "correctness": review.content["correctness"],
                        "technical_novelty_and_significance": review.content["technical_novelty_and_significance"],
                        "empirical_novelty_and_significance": review.content["empirical_novelty_and_significance"],
                        "flag_for_ethics_review": review.content["flag_for_ethics_review"],
                        "recommendation": review.content["recommendation"],
                        "confidence": review.content["confidence"],
                        }
            elif venue_year == 2023:
                record = {"id": review.id, #str
                          "replyto": review.replyto, # id of submission (str)
                          "tcdate": review.tcdate,
                          "tmdate": review.tmdate,
                        
                        # ------ content -------
                        "confidence": review.content["confidence"],
                        "summary_of_the_paper": review.content["summary_of_the_paper"],
                        "strength_and_weaknesses": review.content["strength_and_weaknesses"],
                        "clarity,_quality,_novelty_and_reproducibility": review.content["clarity,_quality,_novelty_and_reproducibility"],
                        "summary_of_the_review": review.content["summary_of_the_review"],
                        "correctness": review.content["correctness"],
                        "technical_novelty_and_significance": review.content["technical_novelty_and_significance"],
                        "empirical_novelty_and_significance": review.content["empirical_novelty_and_significance"],
                        "flag_for_ethics_review": review.content["flag_for_ethics_review"],
                        "recommendation": review.content["recommendation"],
                        }
            review_records.append(record)

    print(f"found {len(review_records)} records")
    df = pd.DataFrame.from_records(review_records)
    save_path = os.path.join(str(venue_year), "official_reviews.csv")
    try:
        df.to_csv(save_path, index=False)
    except Exception:
        df.to_csv(save_path, escapechar="\\", index=False)

def _make_comments(client, venue_year):
    """Create official_comments.csv"""
    
    comment_records = []
    submissions = pd.read_csv(os.path.join(str(venue_year), "submissions.csv"))
    for _, submission in tqdm(submissions.iterrows()):
        invitation = OFFICIAL_COMMENTS[venue_year] % submission.number
        official_comments = openreview.tools.iterget_notes(client,
                                                           invitation=invitation)
        for official_comment in official_comments:

            if venue_year == 2017:
                if "comment" not in official_comment.content.keys():
                    continue
                by_reviewer = any("Reviewer" in item for item in official_comment.writers)
                record = {"id": official_comment.id,
                        "replyto": official_comment.replyto,
                        "tcdate": official_comment.tcdate, # unix timestamp in milliseconds for true creation date
                        "tmdate": official_comment.tmdate, # unix timestamp in milliseconds for true modification date
                        "writer": "Reviewer" if by_reviewer else "Author",

                        # ------ content ---------
                        "title": official_comment.content["title"] if "title" in official_comment.content.keys() else "", # str
                        "comment": official_comment.content["comment"], # str
                        }
            elif venue_year in [2018, 2019, 2020, 2021, 2022, 2023]:
                if "comment" not in official_comment.content.keys():
                    print("SPENCER 1")
                    continue
                by_author = any("Authors" in item for item in official_comment.writers)
                by_reviewer = any("Reviewer" in item for item in official_comment.writers)
                if not any([by_author, by_reviewer]):
                    print("SPENCER 2")
                    continue
                record = {"id": official_comment.id,
                        "replyto": official_comment.replyto,
                        "tcdate": official_comment.tcdate, # unix timestamp in milliseconds for true creation date
                        "tmdate": official_comment.tmdate, # unix timestamp in milliseconds for true modification date
                        "writer": "Reviewer" if by_reviewer else "Author",

                        # ------ content ---------
                        "title": official_comment.content["title"] if "title" in official_comment.content.keys() else "", # str
                        "comment": official_comment.content["comment"], # str
                        }
            comment_records.append(record)
    print(f"found {len(comment_records)} records")
    df = pd.DataFrame.from_records(comment_records)
    save_path = os.path.join(str(venue_year), "official_comments.csv")
    try:
        df.to_csv(save_path, index=False)
    except Exception:
        df.to_csv(save_path, escapechar="\\", index=False)


if __name__ == "__main__":

    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_path", type=str, default="../credentials.ini") # path to config that contains username and password
    parser.add_argument("--venue_year", type=int)
    args = parser.parse_args()

    USERNAME, PASSWORD = _get_credentials(args.credentials_path)
    client = init_api_v1(USERNAME, PASSWORD)

    # ------ create submissions.csv -------
    #_make_submissions(client, args.venue_year, os.path.join(str(args.venue_year), "submissions.csv"))

    # ------ create official_reviews.csv and official_comments.csv ------
    #_make_reviews(client, arge.venue_year)
    _make_comments(client, args.venue_year)
