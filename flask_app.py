from flask import Flask, jsonify, render_template, url_for, flash, redirect, request
from db.database import db_session
from db.models import UsuariosRT, Termos, Hashtags, HashtagsGraph, UsuariosCitados, BigramTrigram, AllTweets
from sqlalchemy.sql.functions import func
from github import Github 
import pytz
import datetime
import calendar
import configparser
import operator
import math
import json
import pprint
import geojson

from geojson import Feature, Point, FeatureCollection

from collections import Counter

from sqlalchemy import and_

from scripts.d2l_collector.twitter import Twitter

from scripts.d2l_processing.processing import Processing

from twython import Twython

app = Flask(__name__)
 
TEMPLATES_AUTO_RELOAD = True
config = configparser.ConfigParser()
config.read("config.ini")

SIDE_A = config['GENERAL']['SIDE_A']
SIDE_B = config['GENERAL']['SIDE_B']
CONTEXT = config['GENERAL']['CONTEXT']
HASHTAG = config['GENERAL']['HASHTAG']

PROFILE_A = config['PROFILES']['PROFILE_A']
PROFILE_B = config['PROFILES']['PROFILE_B']
TOPICS = config['PROFILES']['TOPICS']

items_per_page = 10


def change_fuso(value):

    fuso_horario = pytz.timezone("America/Sao_Paulo")
    date_ = value.replace(tzinfo=pytz.utc)
    date_ = date_.astimezone(fuso_horario)
    str_time = date_.strftime("%Y-%m-%d %H:%M:%S")

    return str_time

def format_datetime(value):

    fuso_horario = pytz.timezone("America/Sao_Paulo")
    date_ = value.replace(tzinfo=pytz.utc)
    date_ = date_.astimezone(fuso_horario)
    str_time = date_.strftime("%d/%m/%y %H:%M:%S")

    return str_time

app.jinja_env.filters['datetime'] = format_datetime

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


def load_from_db(limit=10):

    query_usuarios_rt = UsuariosRT.query.filter(UsuariosRT.context.is_(CONTEXT)).order_by(UsuariosRT.frequencia.desc()).limit(limit).all()
    query_termos = Termos.query.filter(Termos.context.is_(CONTEXT)).order_by(Termos.frequencia.desc()).limit(limit).all()
    query_hashtags = Hashtags.query.filter(Hashtags.context.is_(CONTEXT)).order_by(Hashtags.frequencia.desc()).limit(limit).all()
    query_usuarios_citados = UsuariosCitados.query.filter(UsuariosCitados.context.is_(CONTEXT)).order_by(UsuariosCitados.frequencia.desc()).limit(limit).all()

    query_bigram_trigram = BigramTrigram.query.filter(BigramTrigram.context.is_(CONTEXT)).order_by(BigramTrigram.frequencia.desc()).limit(limit).all()

    return query_termos, query_hashtags, query_usuarios_rt, query_usuarios_citados, query_bigram_trigram

@app.route("/")
@app.route("/home")
def home():

    total_texts = db_session.query(func.count(AllTweets.id).label('total_texts')).filter(AllTweets.context.is_(CONTEXT)).first().total_texts


    total_terms = db_session.query(func.count(Termos.id).label('total_terms')).filter(Termos.context.is_(CONTEXT)).first().total_terms
    total_processed = db_session.query(func.count(AllTweets.id).label("total_processed")).filter(AllTweets.context.is_(CONTEXT)).filter(AllTweets.processed==1).first().total_processed
    

    date_max = db_session.query(AllTweets.id, func.max(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date
    date_min = db_session.query(AllTweets.id, func.min(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date

    termos, hashtags, usuarios_rt, usuarios_citados, bigram_trigram = load_from_db(10)


    if HASHTAG == "True":
        query_a = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_A),Hashtags.context.is_(CONTEXT))).first()
        query_b = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_B),Hashtags.context.is_(CONTEXT))).first()
    else:
        query_a = Termos.query.filter(and_(Termos.termo.is_(SIDE_A),Termos.context.is_(CONTEXT))).first()
        query_b = Termos.query.filter(and_(Termos.termo.is_(SIDE_B),Termos.context.is_(CONTEXT))).first()

    total_a = 0
    total_b = 0
    percent_a = 0
    percent_b = 0
    total = 0

    if query_a and query_b:
        total_a = float(query_a.frequencia)
        total_b = float(query_b.frequencia)

        total = total_a + total_b

        percent_a = (total_a / total) * 100
        percent_b = (total_b / total) * 100

    
    profiles_info = get_profile()

    query_texts = db_session.query(AllTweets)
    all_ = []
    for q in query_texts:

        teste = q.text.decode('UTF-8')

        t = {}
        t['tweet_id'] = q.tweet_id
        t['user'] = q.user
        t['text'] = teste
        t['date'] = q.date
        all_.append(t)

    tweets = jsonify(**{'list': all_})


    dict_values = {
        'total_texts': total_texts,
        'total_terms': total_terms,
        'total_processed': total_processed,
        'date_max': date_max,
        'date_min': date_min,
        'side_a': SIDE_A,
        'side_b': SIDE_B,
        'termos': termos,
        'hashtags': hashtags,
        'usuarios_rt': usuarios_rt,
        'usuarios_citados': usuarios_citados,
        'total': (percent_a, percent_b),
        'total_value': (int(total_a), int(total_b)),
        'bigram_trigram': bigram_trigram,
        'context': CONTEXT,
        'profile_a': PROFILE_A,
        'profile_b': PROFILE_B,
        'dict_profile': profiles_info
    }

    """
        ------------------Paginação---------------------
    """
    
    current_page = request.args.get('page', 1, type=int)

    num_posts = total_texts
    total_num_pages = int(math.ceil(num_posts / items_per_page))
    iter_pages = list(range(1, total_num_pages + 1))

    """
        ------------------Paginação---------------------
    """


    return render_template("home.html",values=dict_values, tweets=all_, iter_pages=iter_pages,
                           current_page=current_page, total_pages=total_num_pages)

@app.route("/analysis")
def analysis():

    total_texts = db_session.query(func.count(AllTweets.id).label('total_texts')).filter(AllTweets.context.is_(CONTEXT)).first().total_texts

    total_terms = db_session.query(func.count(Termos.id).label('total_terms')).filter(Termos.context.is_(CONTEXT)).first().total_terms
    total_processed = db_session.query(func.count(AllTweets.id).label("total_processed")).filter(AllTweets.context.is_(CONTEXT)).filter(AllTweets.processed==1).first().total_processed
    
    date_max = db_session.query(AllTweets.id, func.max(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date
    date_min = db_session.query(AllTweets.id, func.min(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date

    termos, hashtags, usuarios_rt, usuarios_citados, bigram_trigram = load_from_db(10)

    if HASHTAG == "True":
        query_a = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_A),Hashtags.context.is_(CONTEXT))).first()
        query_b = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_B),Hashtags.context.is_(CONTEXT))).first()
    else:
        query_a = Termos.query.filter(and_(Termos.termo.is_(SIDE_A),Termos.context.is_(CONTEXT))).first()
        query_b = Termos.query.filter(and_(Termos.termo.is_(SIDE_B),Termos.context.is_(CONTEXT))).first()

    total_a = 0
    total_b = 0
    percent_a = 0
    percent_b = 0
    total = 0

    if query_a and query_b:
        total_a = float(query_a.frequencia)
        total_b = float(query_b.frequencia)

        total = total_a + total_b

        percent_a = (total_a / total) * 100
        percent_b = (total_b / total) * 100

    profiles_info = get_profile()

    query_texts = db_session.query(AllTweets)
    all_ = []
    for q in query_texts:

        teste = q.text.decode('UTF-8')

        t = {}
        t['tweet_id'] = q.tweet_id
        t['user'] = q.user
        t['text'] = teste
        t['date'] = q.date
        all_.append(t)

    tweets = jsonify(**{'list': all_})

    dict_values = {
        'total_texts': total_texts,
        'total_terms': total_terms,
        'total_processed': total_processed,
        'date_max': date_max,
        'date_min': date_min,
        'side_a': SIDE_A,
        'side_b': SIDE_B,
        'termos': termos,
        'hashtags': hashtags,
        'usuarios_rt': usuarios_rt,
        'usuarios_citados': usuarios_citados,
        'total': (percent_a, percent_b),
        'total_value': (int(total_a), int(total_b)),
        'bigram_trigram': bigram_trigram,
        'context': CONTEXT,
        'profile_a': PROFILE_A,
        'profile_b': PROFILE_B,
        'dict_profile': profiles_info
    }

    return render_template('analysis.html', values=dict_values, title='Analysis')

@app.route("/analysis/cloud/")
def cloud():

    query_termos = Termos.query.filter(Termos.context.is_(CONTEXT)).order_by(Termos.frequencia.desc()).limit(400).all()

    t = {}

    for q in query_termos:
        if q.termo != SIDE_A and q.termo != SIDE_B:
            t[q.termo] = q.frequencia

    return jsonify(**t)

@app.route("/analysis/graph/")
def graph():

    query_hashtag = HashtagsGraph.query.filter_by(context=CONTEXT).all()
    all_ = []

    fuso_horario = pytz.timezone("America/Sao_Paulo")

    for q in query_hashtag:

        
        date_ = change_fuso(q.date)

        
        
        t = {}
        t['date'] = date_
        t['count'] = q.frequencia
        t['hashtag'] = q.hashtag
        all_.append(t)

    return jsonify(**{'list': all_})


@app.route("/map")
def map():

    total_texts = db_session.query(func.count(AllTweets.id).label('total_texts')).filter(AllTweets.context.is_(CONTEXT)).first().total_texts

    total_terms = db_session.query(func.count(Termos.id).label('total_terms')).filter(Termos.context.is_(CONTEXT)).first().total_terms
    total_processed = db_session.query(func.count(AllTweets.id).label("total_processed")).filter(AllTweets.context.is_(CONTEXT)).filter(AllTweets.processed==1).first().total_processed
    
    date_max = db_session.query(AllTweets.id, func.max(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date
    date_min = db_session.query(AllTweets.id, func.min(AllTweets.date).label('last_date')).filter(AllTweets.context.is_(CONTEXT)).first().last_date

    termos, hashtags, usuarios_rt, usuarios_citados, bigram_trigram = load_from_db(10)

    if HASHTAG == "True":
        query_a = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_A),Hashtags.context.is_(CONTEXT))).first()
        query_b = Hashtags.query.filter(and_(Hashtags.hashtag.is_(SIDE_B),Hashtags.context.is_(CONTEXT))).first()
    else:
        query_a = Termos.query.filter(and_(Termos.termo.is_(SIDE_A),Termos.context.is_(CONTEXT))).first()
        query_b = Termos.query.filter(and_(Termos.termo.is_(SIDE_B),Termos.context.is_(CONTEXT))).first()

    total_a = 0
    total_b = 0
    percent_a = 0
    percent_b = 0
    total = 0

    if query_a and query_b:
        total_a = float(query_a.frequencia)
        total_b = float(query_b.frequencia)

        total = total_a + total_b

        percent_a = (total_a / total) * 100
        percent_b = (total_b / total) * 100

    profiles_info = get_profile()

    query_texts = db_session.query(AllTweets)
    all_ = []
    for q in query_texts:

        teste = q.text.decode('UTF-8')

        t = {}
        t['tweet_id'] = q.tweet_id
        t['user'] = q.user
        t['text'] = teste
        t['date'] = q.date
        all_.append(t)

    tweets = jsonify(**{'list': all_})

    dict_values = {
        'total_texts': total_texts,
        'total_terms': total_terms,
        'total_processed': total_processed,
        'date_max': date_max,
        'date_min': date_min,
        'side_a': SIDE_A,
        'side_b': SIDE_B,
        'termos': termos,
        'hashtags': hashtags,
        'usuarios_rt': usuarios_rt,
        'usuarios_citados': usuarios_citados,
        'total': (percent_a, percent_b),
        'total_value': (int(total_a), int(total_b)),
        'bigram_trigram': bigram_trigram,
        'context': CONTEXT,
        'profile_a': PROFILE_A,
        'profile_b': PROFILE_B,
        'dict_profile': profiles_info
    }

    def push_github():

        data = []
        geoms = []
        tweet_features = []
        with open('raw.json') as twtr_hamdata:    
            for satir in twtr_hamdata:
                data.append(json.loads(satir))

        for i in range(0,len(data)):
            geoms.append(data[i]["geo"]["coordinates"])
            #print (geoms[i][0], geoms[i][1])
            my_feature = Feature(geometry=Point((float(geoms[i][1]),float(geoms[i][0]))),\
            properties={"user_location":data[i]["user"]["location"],\
            "user_id": data[i]["id"],\
            "user_name":data[i]["user"]["name"],\
            "screen_name":data[i]["user"]["screen_name"],\
            "followers_count":data[i]["user"]["followers_count"],\
            "tweet":data[i]["text"],\
            "tweet_time":data[i]["created_at"]})
            tweet_features.append(my_feature)
	        #print tweet_features
        tweet_FeatureCollection = FeatureCollection(tweet_features[:])
        #print tweet_FeatureCollection["type"]
        try:
            #saveFile = open('tweets.geojson','a')
            data = json.dumps(tweet_FeatureCollection)
            #saveFile.close()
        except Exception as error:
            print ("Unable to write %s error"%error)


        g = Github('grandslav', '5kslj8130614')
        repo = g.get_user().get_repo("GeoJSONTweets")
        contents = repo.get_contents("/tweets.geojson")
        new_content = data
        # TODO: acrescentar arquivo em vez de substituir ("crimes01112018.geojson")
        repo.update_file("/tweets.geojson", "Updating geojson data", new_content, contents.sha)
        print("Arquivo .geojson atualizado")

    update = True
    if update:
        print("Atualizando geojson...")
        push_github()  # faz um push no repositorio com arquivo geojson atualizado

    return render_template('map.html', values=dict_values, title='Map')


def get_profile():

    

    twitter = Twitter()
    credentials = twitter.get_credentials()
    tw = Twython(credentials['consumer_key'], credentials['consumer_secret'], credentials['access_token'], credentials['access_token_secret'])

    tw_user_a = tw.show_user(screen_name=PROFILE_A)
    tw_user_b = tw.show_user(screen_name=PROFILE_B)

    user_a = {
        'name': tw_user_a['name'],
        'description': tw_user_a['description'],
        'photo': tw_user_a['profile_image_url']
    }

    user_b = {
        'name': tw_user_b['name'],
        'description': tw_user_b['description'],
        'photo': tw_user_b['profile_image_url']
    }

    dict_ = {
        'A': user_a,
        'B': user_b
    }

    
    return dict_

@app.route("/profile_temp")
def profile_temp():

    args = {}

    return render_template("out.html",values=args)


@app.route("/profile")
def profile():
    

    return render_template("profile.html")    


@app.route("/profile_information", methods=['POST'])
def profile_information():

    list_topics = TOPICS.replace(" ", "").split(",")
    

    processing = Processing()

    twitter = Twitter()
    credentials = twitter.get_credentials()
    tw = Twython(credentials['consumer_key'], credentials['consumer_secret'], credentials['access_token'], credentials['access_token_secret'])



    tw_user_a = tw.show_user(screen_name=PROFILE_A)
    tw_user_b = tw.show_user(screen_name=PROFILE_B)

    user_a = {
        'name': tw_user_a['name'],
        'description': tw_user_a['description'],
        'photo': tw_user_a['profile_image_url']
    }

    user_b = {
        'name': tw_user_b['name'],
        'description': tw_user_b['description'],
        'photo': tw_user_b['profile_image_url']
    }

    timeline_a = tw.get_user_timeline(screen_name=PROFILE_A, count=200)
    timeline_b = tw.get_user_timeline(screen_name=PROFILE_B, count=200)

    args = {}

    all_texts_a = []
    all_texts_b = []

    for tweet in timeline_a:
        tweet_data = twitter.get_tweet_data(tweet)
        all_texts_a.append(tweet_data['text'])

    for tweet in timeline_b:
        tweet_data = twitter.get_tweet_data(tweet)
        all_texts_b.append(tweet_data['text'])

    words_a, hashtags_a, topics_a = processing.get_words_simple(all_texts_a, list_topics)
    words_b, hashtags_b, topics_b = processing.get_words_simple(all_texts_b, list_topics)

    
    temp_a = dict(Counter(words_a).most_common(250))
    temp_b = dict(Counter(words_b).most_common(250))
    sorted_a = dict(sorted(temp_a.items(), key=operator.itemgetter(1), reverse=True))
    sorted_b = dict(sorted(temp_b.items(), key=operator.itemgetter(1), reverse=True))

    top_10_a = [word for word in sorted_a][:10]
    top_10_b = [word for word in sorted_b][:10]

    user_a['top_10'] = top_10_a
    user_b['top_10'] = top_10_b

    user_a['words'] = sorted_a
    user_b['words'] = sorted_b

    user_a['hashtags'] = Counter(hashtags_a).most_common(3)
    user_b['hashtags'] = Counter(hashtags_b).most_common(3)

    user_a['topics'] = dict(Counter(topics_a))
    user_b['topics'] = dict(Counter(topics_b))

    args = {
        'user_a': user_a,
        'user_b': user_b,
        'topics_name': list_topics
    }

    return jsonify(args)

if __name__ == "__main__":
    
    app.run(debug=True)

def update_geojson():
    """
        Verifica se eh necessario atualizar arquivo .geojson no github com novos crimes.
        Para evitar atualizacao do documento a cada acesso ao site, resolvemos criar uma condicao:
            Se o ultimo commit ocorreu a mais de 30 dias, atualizamos o geojson
            Se nao, apresentamos os dados com base no ultimo arquivo do repositorio
    """
    g = Github(#LOGIN DO GITHUB#, #SENHA DO GITHUB#)
    repo = g.get_user().get_repo("GeoJSONTweets")
    commits = repo.get_commits()
    last_date = commits[0].last_modified  # recupera data do ultimo commit feito no repositorio
    last_date = datetime.datetime.strptime(last_date, "%a, %d %b %Y %X %Z").replace(tzinfo=datetime.timezone.utc)
    actual_date = datetime.datetime.now(datetime.timezone.utc)  # .strftime("%Y-%m-%d %H:%M:%S")
    delta = actual_date - last_date
    print(
        "\nMensagem ultimo commit: {}\nUltima modificacao: {}\nIntervalo: {} dia(s)\n".format(commits[0].commit.message,
                                                                                              last_date, delta.days))
    # if (actual_date - last_date).days >= 3:
    #     return True
    # return False
    return True


def push_github():
    g = Github(#LOGIN DO GITHUB#, #SENHA DO GITHUB#)
    repo = g.get_user().get_repo("GeoJSONTweets")
    contents = repo.get_contents("/tweets.geojson")
    new_content = json.dumps(data)
    # TODO: acrescentar arquivo em vez de substituir ("crimes01112018.geojson")
    repo.update_file("/tweets.geojson", "Updating geojson data", new_content, contents.sha)
    print("Arquivo .geojson atualizado")