import time
import pytz
import sys

from sqlalchemy import exc

from db.models import AllTweets
from db.database import db_session


from datetime import datetime
from twython import Twython
from mapbox import Geocoder
import json
from scripts.d2l_collector.twitter import Twitter

class TwitterCollector():

    def __init__(self):

        self.twitter = Twitter()
        self.credentials = self.twitter.get_credentials()
        self.twython = Twython(self.credentials['consumer_key'], self.credentials['consumer_secret'], self.credentials['access_token'], self.credentials['access_token_secret'])
        


    def collect(self, query, context, waiting_time, count, number_of_attempts):

        def find(word, letter):
            for l in word:
                if l == letter:
                    return True
            return False
      
        if query == '':
            return

        geocoder = Geocoder(access_token="pk.eyJ1IjoiZ3Jhbmhva2FpbiIsImEiOiJjam8wbXdyeDIwMXprM3Bubm04ZnUyYzRqIn0.XKzTzY7qAr44O8hU2M2agA")

        tweets_collect = []
        list_ids = []

        for i in range(0, number_of_attempts):

            print("Collecting " + query + "... Attempt: " + str(i))

            if i == 0:
                results = self.twython.search(q=query, count=count, lang='pt')
            else:
                results = self.twython.search(q=query, count=count, lang='pt', max_id=last_since)

            #count_control = 0
            tweets = results['statuses']
            indice = len(tweets)-1
            last_tweet = tweets[indice]
            last_since = last_tweet['id']

            for t in results['statuses']:
                
                tweet = self.twitter.get_tweet_data(t)
                
                try:
                    user_ = t['user']
                    _location = user_['location']
                    saveFile = open('raw.json','a')
                    if _location == None:
                        #print (':(   User %s is not sharing location'%t['user']['screen_name'])
                        saveFile.close()
                    else:
                        if find(_location, ',') == False:
                            #print (':(   User %s is sharing wrong location'%t['user']['screen_name'])
                            saveFile.close()
                        else:
                            coordinates = geocoder.forward(_location)
                            if coordinates.geojson()['features'] == []:
                                #print (':(   User %s is sharing wrong city'%t['user']['screen_name'])
                                saveFile.close()
                            else:
                                mapboxResponse = coordinates.geojson()['features'][0]
                                coordinates_ = mapboxResponse['geometry']['coordinates']
                                t['geo'] = {"type":"Point","coordinates":(coordinates_[1],coordinates_[0])}
                                novo_tweet = json.dumps(t)
                                saveFile.write(novo_tweet+'\n')
                                saveFile.close()
                    #Collecting all here        
                                tweet_instance = AllTweets(tweet['object_id'], tweet['user_name'], tweet['text'], tweet['date_formated'], tweet['user_rt'], tag, context)
                                db_session.add(tweet_instance)
                                db_session.commit()
                                print("Saved " + str(tweet['object_id']))
                except exc.IntegrityError as e:
                    print("The tweet " + str(tweet['object_id']) + " has already on database")
                    db_session.rollback()
                except Exception as e:
                    raise Exception("Database Error: " + str(e))
                
                
            
            #waiting_time in seconds
            print("Waiting Sleep Time ...")
            time.sleep(waiting_time)


        

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

    tw = TwitterCollector()
    tw.collect(tag, context, 5, 100, 10)

    
    