import pandas as pd
import sys
import os
from configparser import ConfigParser

from Scraper import Scraper

config = ConfigParser()
config.read('config.ini')

# Setting the execution mode
headless_option = len(sys.argv) >= 2 and sys.argv[1].upper() == 'HEADLESS'

path = config.get('profiles_data', 'path')
input_file_name = config.get('profiles_data', 'input_file_name')
profiles = pd.read_csv(path + input_file_name)

collected_ids = []
if 'collected_ids.csv' in os.listdir(path + "linkedin_data/"):
    with open(path + 'linkedin_data/collected_ids.csv') as file:
        collected_ids += file.read().splitlines()

if 'error_ids.csv' in os.listdir(path + "linkedin_data/"):
    with open(path + 'linkedin_data/error_ids.csv') as file:
        collected_ids += file.read().splitlines()

profiles = profiles[~profiles.id.isin(collected_ids)].reset_index().loc[3:]



profiles_urls = profiles.linkedin.values
profiles_urls = ['https://www.linkedin.com/in/lukasz-poczesny/']
profiles_ids = profiles.id.values
profiles_ids = [0]

if len(profiles_urls) == 0:
    print("Please provide an input.")
    sys.exit(0)


# Launch Scraper
s = Scraper(
    linkedin_username=config.get('linkedin', 'username'),
    linkedin_password=config.get('linkedin', 'password'),
    profiles_urls=profiles_urls,
    headless=headless_option,
    output_file_path = path + "linkedin_data/",
    ids = profiles_ids
)

s.start()

s.join()

print("Scraping Ended")
