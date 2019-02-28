# coding=utf8

# Import dos pacotes necessários do Twython
from twython import TwythonStreamer
from twython import Twython

# Import métodos para tratar a data
from datetime import datetime
import pytz
import sys 
import time

from db.models import AllTweets
from db.database import db_session

from sqlalchemy import exc

from scripts.d2l_collector.twitter import Twitter


class MyStreamer(TwythonStreamer):

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, twitter_instance):
        self.twitter = twitter_instance
        TwythonStreamer.__init__(self, consumer_key, consumer_secret, access_token, access_token_secret)

    def set_stringsearch(self, tag):
        self.hashtag = tag

    def set_context(self, context):
        self.context = context

    def on_success(self, data):

        tweet = self.twitter.get_tweet_data(data)

        try:
            tweet_instance = AllTweets(tweet['object_id'], tweet['user_name'], tweet['text'], tweet['date_formated'], tweet['user_rt'], self.hashtag, self.context)
            db_session.add(tweet_instance)
            db_session.commit()
        except exc.IntegrityError as e:
            print("The tweet " + str(tweet['object_id']) + " has already on database")
            db_session.rollback()
        except Exception as e:
            raise Exception("Database Error: " + str(e))

        print("Saved: " + str(tweet['object_id']))
        

    def on_error(self, status_code, data):
        print("Erro to collected streamming " + str(status_code))
        self.disconnect()



if __name__ == "__main__":

    p = sys.argv

    if len(p) < 3:
        print("Number of arguments is not correct")
        exit(0)
    elif len(p) == 3:
        tag = str(p[1])
        context = str(p[2])
        language = None
    else:
        tag = str(p[1])
        context = str(p[2])
        language = str(p[3])
    
    twitter = Twitter()

    credentials = twitter.get_credentials()

    consumer_key = credentials['consumer_key'] 
    consumer_secret = credentials['consumer_secret'] 
    access_token = credentials['access_token'] 
    access_token_secret = credentials['access_token_secret'] 

    stream = MyStreamer(consumer_key, consumer_secret, access_token, access_token_secret, twitter)
    stream.set_stringsearch(tag)
    stream.set_context(context)
    
    try:
        if language == None:
            stream.statuses.filter(track=tag)
        else:
            stream.statuses.filter(track=tag, language=language)
    except Exception as e:

        print("An error ocurred ... Waiting 30s to restart collected.")
        print("Error description: " + str(e))
        time.sleep(30)
        if language == None:
            stream.statuses.filter(track=tag)
        else:
            stream.statuses.filter(track=tag, language=language)