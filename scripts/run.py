import os
import sys
import time
import pytz

from collections import Counter
from datetime import datetime
from unicodedata import normalize

from nltk.tokenize import regexp_tokenize
from sqlalchemy import and_

from db.database import db_session
from db.models import (AllTweets, BigramTrigram, Hashtags, HashtagsGraph,
                       Termos, UsuariosCitados, UsuariosRT)

from scripts.d2l_processing.processing import Processing

import configparser



def start(context_=None, side_tuple=None, limit=100):

    print("Processing Tweets ...")

    processor = Processing()
    
    tweets = db_session.query(AllTweets).filter(and_(AllTweets.processed.is_(0), AllTweets.context.is_(context_))).limit(limit)

    if tweets.count() > 0:

        all_texts = []
        all_users_rt = []

        for tweet in tweets:
            tweet.processed = 1
            
            tuple_text = (tweet.text, tweet.date)

            all_texts.append(tuple_text)
            
            if tweet.rt_user != "":
                all_users_rt.append(tweet.rt_user)
            
        db_session.commit()

        final_words, all_tokens_date = processor.get_final_words(all_texts, False, (side_tuple[0], side_tuple[1]))

        dict_ = {}

        for token in all_tokens_date:
            str_date = str(token[1]).split(" ")[0] + " " + str(token[1]).split(" ")[1].split(":")[0] + ":00"
            
            if str_date in dict_.keys():
                dict_[str_date] += token[0]
            else:
                dict_[str_date] = token[0]


        frequency_terms = processor.get_frequence_terms(final_words)
        frequency_users_rt = processor.get_frequence_users_rt(all_users_rt)
        
        frequency_users_cited = processor.get_frequence_users_cited()
        frequency_hashtags = processor.get_frequence_hashtags()

        bigrams, trigrams = processor.get_bigrams_trigrams(final_words)
        
        # Insert in database
        print("Populating database ... ")
        populate_database(context_, side_tuple, bigrams, frequency_hashtags, frequency_terms, frequency_users_rt, frequency_users_cited, trigrams, dict_)
    else:
        print("All tweets was processed")
    

def populate_database(context, side_tuple, bigrams, frequency_hashtags, frequency_terms, frequency_users_rt, frequency_users_cited, trigrams, hashtag_date):

    side_a = side_tuple[0]
    side_b = side_tuple[1]
    
    for t in frequency_terms:

        obj = db_session.query(Termos).filter(and_(Termos.termo.is_(t[0]),Termos.context.is_(context))).first()

        if obj == None:
	        termo = Termos(t[0], t[1], context)
	        db_session.add(termo)
        else:
	        obj.frequencia = obj.frequencia + t[1]
    
    db_session.commit()
    
    for t in frequency_users_rt:

        obj = db_session.query(UsuariosRT).filter(and_(UsuariosRT.usuario.is_(t[0]),UsuariosRT.context.is_(context))).first()

        if obj == None:
            new_ = UsuariosRT(t[0], t[1], context)
            db_session.add(new_)
        else:
            obj.frequencia = obj.frequencia + t[1]
    
    db_session.commit()
    
    for t in frequency_users_cited:

        obj = db_session.query(UsuariosCitados).filter(and_(UsuariosCitados.usuario.is_(t[0]),UsuariosCitados.context.is_(context))).first()
        
        if obj == None:
            new_ = UsuariosCitados(t[0], t[1], context)
            db_session.add(new_)
        else:
            obj.frequencia = obj.frequencia + t[1]

    db_session.commit()
    
    for t in frequency_hashtags:

        obj = db_session.query(Hashtags).filter(and_(Hashtags.hashtag.is_(t[0]), Hashtags.context.is_(context))).first()

        if obj == None:
            new_ = Hashtags(t[0], t[1], context)
            db_session.add(new_)
        else:
            obj.frequencia = obj.frequencia + t[1]

    db_session.commit()
    
    for bigram in bigrams:
        text = ' '.join(word for word in bigram)
        
        obj = db_session.query(BigramTrigram).filter(and_(BigramTrigram.text.is_(text), BigramTrigram.context.is_(context))).first()

        if obj == None:
            new_ = BigramTrigram(text, 1, context)
            db_session.add(new_)
        else:
            obj.frequencia = obj.frequencia + 1
    
    db_session.commit()
    
    for trigram in trigrams:
        text = ' '.join(word for word in trigram)

        obj = db_session.query(BigramTrigram).filter(and_(BigramTrigram.text.is_(text), BigramTrigram.context.is_(context))).first()

        if obj == None:
            new_ = BigramTrigram(text, 1, context)
            db_session.add(new_)
        else:
            obj.frequencia = obj.frequencia + 1
    
    db_session.commit()

    for d in sorted(hashtag_date):
        hashtag_date[d] = [w for w in hashtag_date[d] if w in [side_a, side_b]]
        dict_counter = Counter(hashtag_date[d])
        

        fmt = '%Y-%m-%d %H:%M'
        new_date = datetime.strptime(d, fmt).replace(tzinfo=pytz.UTC)

        obj_a = db_session.query(HashtagsGraph).filter(and_(HashtagsGraph.hashtag.is_(side_a), HashtagsGraph.date.is_(new_date), HashtagsGraph.context.is_(context))).first()
        obj_b = db_session.query(HashtagsGraph).filter(and_(HashtagsGraph.hashtag.is_(side_b), HashtagsGraph.date.is_(new_date), HashtagsGraph.context.is_(context))).first()

        if obj_a == None:

            new_data = HashtagsGraph(side_a, dict_counter[side_a], new_date, context)
            db_session.add(new_data)
        else:
            obj_a.frequencia = obj_a.frequencia + dict_counter[side_a]

        if obj_b == None:
            new_data = HashtagsGraph(side_b, dict_counter[side_b], new_date, context)
            db_session.add(new_data)
        else:
            obj_b.frequencia = obj_b.frequencia + dict_counter[side_b]

    db_session.commit()


if __name__ == "__main__":


    config = configparser.ConfigParser()
    config.read("config.ini")

    CONTEXT = config['GENERAL']['CONTEXT']
    SIDE_A = config['GENERAL']['SIDE_A']
    SIDE_B = config['GENERAL']['SIDE_B']

    while(True):
        start(context_=CONTEXT, side_tuple=(SIDE_A, SIDE_B), limit=100)
        print("Waiting ... ")
        time.sleep(10)
