#coding=utf-8
'''

    A simple script to collect tweets by ids.

    Replace the values in consumer_key, consumer_secret, access_token, access_token_secret

    @TODO: Implement more complete script: (1) avoid limit rate, (2) stop and restart script where the script stop (in case of error)

'''

import csv
import os
import sys
import time
from datetime import datetime

import pytz
from sqlalchemy.exc import IntegrityError
from twython import Twython
from twython.exceptions import TwythonError, TwythonRateLimitError

from db.database import db_session
from db.models import AllTweets
from scripts.d2l_collector.twitter import Twitter

parent_dir_name = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

t = Twitter()
credentials = t.get_credentials()


tw = Twython(credentials['consumer_key'], credentials['consumer_secret'], credentials['access_token'], credentials['access_token_secret'])

result = []
count = 0

context = "bvs"
tag = "#teambatman OR #teamsuperman"

with open(parent_dir_name + '/files/tweets_ids.csv', 'rt', encoding="utf-8") as csv_file:
    reader = csv.DictReader(csv_file)
    all_tweets = []
    for row in reader:
        print("Collecting " + str(row['tweet_id']))

        tweet_id = row['tweet_id']

        try:
            tweet = tw.show_status(id=tweet_id)

            tweet_processed = t.get_tweet_data(tweet)

            tweet_instance = AllTweets(tweet_processed['object_id'], tweet_processed['user_name'], tweet_processed['text'], tweet_processed['date_formated'], tweet_processed['user_rt'], tag, context)
            db_session.add(tweet_instance)
            db_session.commit()

            count = count + 1
            print("\t " + str(count) + " tweets collected")

        except TwythonRateLimitError as e:
            print("Limit Error. Waiting 15 minutes")
            time.sleep(900)
        except TwythonError as e:
            print("\tERROR: " + str(tweet_id) + " not collected: " + str(e))
        except IntegrityError as e:
            print("\tERROR: " + str(tweet_id) + " not inserted at db: tweet id is already in database")
            db_session.rollback()
        except Exception as e:
            print("\ERROR: " + str(tweet_id + ": " + str(e)))
