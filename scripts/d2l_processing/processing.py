import nltk
import pytz

from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.corpus import stopwords
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures
from nltk.tokenize import regexp_tokenize

from collections import Counter, Set
from unicodedata import category, normalize

from scripts.d2l_utils.repeatreplacer import RepeatReplacer


class Processing():

    def __init__(self, stopwords_language=['portuguese']):
        self.pattern = r'(https://[^"\' ]+|www.[^"\' ]+|http://[^"\' ]+|\w+|\@\w+|\#\w+)'
        self.pattern_user = r'\@\w+'
        self.pattern_links = r'(https://[^"\' ]+|www.[^"\' ]+|http://[^"\' ]+)'
        self.pattern_hashtag = r'\#\w+'
        self.pattern_words = r'\w+'

        self.portuguese_stops = stopwords.words(stopwords_language)

        self.users_cited = []
        self.links_appears = []
        self.hashtags = []

    def encode_text(self, text):

        new_text = str(text, 'utf-8')

        try:
            new_text = normalize('NFKD', new_text.lower()).encode('ASCII', 'ignore')
        except UnicodeEncodeError:
            new_text = normalize('NFKD', new_text.lower().decode('utf-8')).encode('ASCII', 'ignore')

        if isinstance(new_text, str) == False:
            new_text = new_text.decode('utf-8')

        return new_text

    def get_words_simple(self, list_text, list_topics):

        all_tokens = []
        all_hashtags = []

        for text in list_text:
            tweet_text = self.encode_text(text).lower()
            
            
            local_patterns = regexp_tokenize(tweet_text, self.pattern)
            users = regexp_tokenize(tweet_text, self.pattern_user)
            links = regexp_tokenize(tweet_text, self.pattern_links)
            hashtags = regexp_tokenize(tweet_text, self.pattern_hashtag)
            
            all_hashtags += hashtags


            final_tokens = [e for e in local_patterns if e not in links]
            final_tokens = [e for e in final_tokens if e not in hashtags]
            final_tokens = [e for e in final_tokens if e not in users]

            all_tokens += final_tokens

        words = [word for word in all_tokens if word not in self.portuguese_stops]
        final_words = [word for word in words if len(word) >= 3]

        topics = [word for word in final_words if word in list_topics]
        
        return final_words, all_hashtags, topics


    def get_words(self, list_text, side_tuple):

        patterns = []
        all_tokens = []
        all_tokens_date = []

        for text in list_text:

            tweet_text = self.encode_text(text[0]).lower()
            
            local_patterns = regexp_tokenize(tweet_text, self.pattern)
            users = regexp_tokenize(tweet_text, self.pattern_user)
            links = regexp_tokenize(tweet_text, self.pattern_links)
            hashtags = regexp_tokenize(tweet_text, self.pattern_hashtag)
            

            self.users_cited += users
            self.links_appears += links
            self.hashtags += hashtags

            tokens_date = [e for e in local_patterns if e == side_tuple[0] or e == side_tuple[1]]

            if len(tokens_date) > 0:
                all_tokens_date.append((tokens_date, text[1]))


            final_tokens = [e for e in local_patterns if e not in links]
            final_tokens = [e for e in final_tokens if e not in hashtags]
            final_tokens = [e for e in final_tokens if e not in users]

            all_tokens += final_tokens

        words = [word for word in all_tokens if word not in self.portuguese_stops]

        word_set = set(words)

        return words, word_set, all_tokens_date


    def correct_text(self, word_set):

        replacer_repeat = RepeatReplacer()

        map_words = {}

        for word in word_set:
            new_word = replacer_repeat.replace(word)
            map_words[word] = new_word

        return map_words

    def get_final_words(self, list_text, correct=True, side_tuple=None):

        words, word_set, all_tokens_date = self.get_words(list_text, side_tuple)

        if correct:
            map_words = self.correct_text(word_set)
            words_temp = [map_words[word] for word in words]
        else:
            words_temp = words

        final_words = [word for word in words_temp if len(word) >= 3]

        return final_words, all_tokens_date

    def get_frequence_terms(self, final_words, limit=None):

        frequence_terms = nltk.FreqDist(final_words)

        if limit:
            return frequence_terms.most_common(limit)
        else:
            return frequence_terms.most_common()


    def get_frequence_users(self, list_user, limit=50):
        frequence_users = nltk.FreqDist(list_user)

        return frequence_users.most_common(limit)


    def get_frequence_users_cited(self, limit=50):
        frequence_users_cited = nltk.FreqDist(self.users_cited)

        return frequence_users_cited.most_common(limit)

    def get_frequence_users_rt(self, list_user_rt, limit=50):
        frequence_users_rt = nltk.FreqDist(list_user_rt)

        return frequence_users_rt.most_common(limit)

    def get_frequence_hashtags(self, limit=50):
        frequence_hashtags = nltk.FreqDist(self.hashtags)

        return frequence_hashtags.most_common(limit)

    def get_bigrams_trigrams(self, final_words, limit=10):

        bcf = BigramCollocationFinder.from_words(final_words)
        tcf = TrigramCollocationFinder.from_words(final_words)

        bcf.apply_freq_filter(3)
        tcf.apply_freq_filter(3)

        result_bi = bcf.nbest(BigramAssocMeasures.raw_freq, limit)
        result_tri = tcf.nbest(TrigramAssocMeasures.raw_freq, limit)

        return result_bi, result_tri
