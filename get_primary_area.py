import argparse
import os
import pandas as pd
from openai import OpenAI
import configparser
import json


def get_credentials(credentials_path):
    """
    Credentials INI file should look like:

    [BASIC]
    SERPER_API_KEY = <api_key>
    OPENAI_API_KEY = <api_key>
    """
    config = configparser.ConfigParser()
    config.read(credentials_path)
    return config["BASIC"]["SERPER_API_KEY"], config["BASIC"]["OPENAI_API_KEY"]


def GetPrimaryArea(client, openai_model_name, abstract, year):
    """
    Input: Abstract of Paper
    Output: Primary Area
    """
    with open("prompts/primary_area.txt", "r") as file:
        prompt = file.read()
    prompt = prompt.replace("{{abstract}}", abstract)
    prompt = prompt.replace("{{year}}", year)
    print(prompt)
    response = client.chat.completions.create(model=openai_model_name,
                                              messages=[{"role": "user",
                                                         "content": prompt}])
    output = response.choices[0].message.content
    print(output)
    return output


def main(args):
    """Entrypoint"""

    dataset = pd.read_csv(os.path.join(args.year, "submissions.csv"))
    dataset = dataset[dataset["outcome"] == "Accepted"].sample(frac=1) # shuffle rows

    SERPER_API_KEY, OPENAI_KEY = get_credentials(args.credentials_path)

    client = OpenAI(api_key=OPENAI_KEY)
    if os.path.exists(args.json_pred_path):
        with open(args.json_pred_path) as file:
            predictions = json.load(file)
    else:
        predictions = {}
    
    for _, row in dataset.iterrows():
        if row["id"] in predictions:
            continue
        abstract = row["abstract"]
        prediction = GetPrimaryArea(client, args.openai_model_name, abstract, args.year)
        
        predictions[row["id"]] = prediction
        
        with open(args.json_pred_path, "w") as file:
            json.dump(predictions, file)


if __name__ == "__main__":
    
    # load arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials_path", type=str, default="../credentials.ini") # path to credentials file
    parser.add_argument("--year", type=str) # path to data
    parser.add_argument("--openai_model_name", type=str, default="gpt-4o-2024-08-06")
    parser.add_argument("--json_pred_path", type=str) # json file to save predictions to
    args = parser.parse_args()

    main(args)