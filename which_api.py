""" Determine which version of OpenReview API to use """
import argparse
import openreview
from utils import _get_credentials


def get_api_version(venue_id, USERNAME, PASSWORD):
    """
    Return API version of venue (either 1 or 2)
    """
    # API V2
    client = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net',
            username=USERNAME, password=PASSWORD)
    group = client.get_group(venue_id)

    if group.domain is not None:
        return 2
    return 1


if __name__ == "__main__":

    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_path", type=str, default="../credentials.ini") # path to config that contains username and password
    parser.add_argument("--venue_id", type=str)
    args = parser.parse_args()

    username, password = _get_credentials(args.credentials_path)
    print(f"found username {username} password {password}")

    api_version = get_api_version(args.venue_id, username, password)
    print(f"venue {args.venue_id} uses api version {api_version}")
