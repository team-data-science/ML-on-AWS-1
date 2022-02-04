#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lambda code that pulls tweets in and saves them to s3 and to a DB
"""

from dateutil import parser
from datetime import datetime
import logging
import json
import os
import pytz
from typing import Optional

from botocore.exceptions import ClientError
import boto3
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd
import psycopg2
import psycopg2.extras
from twython import Twython


try:
    sia = SentimentIntensityAnalyzer()
except LookupError:
    import nltk
    # in lambda you can only write to /tmp folder
    # nltk needs to download data to run a model
    nltk.download('vader_lexicon', download_dir='/tmp')
    # nltk will look for the downloaded data to run SentimentIntensityAnalyzer
    nltk.data.path.append("/tmp")
    sia = SentimentIntensityAnalyzer()


def _time_parser(twitter_time: str) -> datetime:
    '''
    Parse string from twitter api like 'Sat Sep 02 14:25:02 +0000 2021'
    to a datetime object in utc time
    '''
    return parser.parse(twitter_time)


def is_recent(tweet: dict,
              max_time_interval_minutes: int = 5) -> bool:
    '''
    a tweet is recent if it is posted in the last x minutes'
    '''
    time_created = _time_parser(tweet['created_at'])
    now = datetime.now(tz=pytz.UTC)
    # converts time to minutes as the function takes minutes as argument
    seconds_diff = (now-time_created).seconds
    minutes_diff = seconds_diff/60
    is_recent_tweet = minutes_diff <= max_time_interval_minutes
    return is_recent_tweet


def extract_fields(tweet: dict) -> dict:
    '''
    Arbitrary decision to save only some fields of the tweet,
    store them in a different dictionary form which
    is convenient for saving them later
    '''
    author = tweet['user']['screen_name']
    time_created = _time_parser(tweet['created_at'])
    text = tweet['text']
    return dict(author=author,timestamp=time_created, text=text)


def _get_sentiment(string: str) -> float:
    '''
    make sure the score is between -1 (very negative) and 1 (very positive)
    '''
    # sia is the SentimentIntensityAnalyzer object which gives a positive and negative score
    score = sia.polarity_scores(string)
    # we want only 1 score so the negative sentiment will be a negative score 
    # and likewise for the positive
    score = score['neg'] * -1 + score['pos']
    return score

def add_sentiment_score(tweet: dict) -> dict:
    tweet['sentiment_score'] = _get_sentiment(tweet['text'])
    return tweet


def upload_file_to_s3(local_file_name: str,
                      bucket: str,
                      s3_object_name: Optional[str]=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param s3_object_name: If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if s3_object_name is None:
        s3_object_name = local_file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(local_file_name, bucket, s3_object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def get_db_connection() -> psycopg2.extensions.connection:
    # to connect to DB, use the parameters and password that define it
    conn = psycopg2.connect(
                            user="postgres",
                            password=os.environ['DB_PASSWORD'],
                            host=os.environ['DB_HOST'],
                            port="5432",
                            connect_timeout=1)
    return conn


def convert_timestamp_to_int(tweet: dict) ->dict:
    '''datetime object are not serializable for json,
    so we need to convert them to unix timestamp'''
    tweet = tweet.copy()
    tweet['timestamp'] = tweet['timestamp'].timestamp()
    return tweet


def insert_data_in_db(df: pd.DataFrame,
                      conn: psycopg2.extensions.connection,
                      table_name: str = 'tweets_analytics') -> None:
    # you need data and a valid connection to insert data in DB
    are_data = len(df) > 0
    if are_data and conn is not None:
        try:
            cur = conn.cursor()
            # to perform a batch insert we need to reshape the data in 2 strings with the column names and their values
            df_columns = list(df.columns)
            columns = ",".join(df_columns)

            # create VALUES('%s', '%s",...) one '%s' per column
            values = "VALUES({})".format(",".join(["%s" for _ in df_columns]))

            # create INSERT INTO table (columns) VALUES('%s',...)
            # here the final 2 strings are created
            insert_string = "INSERT INTO {} ({}) {}"
            insert_stmt = insert_string.format(table_name, columns, values)
            psycopg2.extras.execute_batch(cur, insert_stmt, df.values)
            conn.commit()
            print('succesful update')

        except psycopg2.errors.InFailedSqlTransaction:
            # if the transaction fails, rollback to avoid DB lock problems
            logging.exception('FAILED transaction')
            cur.execute("ROLLBACK")
            conn.commit()

        except Exception as e:
            # if the transaction fails, rollback to avoid DB lock problems
            logging.exception(f'FAILED  {str(e)}')
            cur.execute("ROLLBACK")
            conn.commit()
        finally:
            # close the DB connection after this
            cur.close()
            conn.close()
    elif conn is None:
        raise ValueError('Connection to DB must be alive!')
    elif len(df) == 0:
        raise ValueError('df has 0 rows!')



def lambda_handler(event, context):
    try:
        # wrap the body into a try/catch to avoid lambda automatically re-trying

        # take the environment variables
        S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
        python_tweets = Twython(os.environ['TWITTER_API_KEY'],
                                os.environ['TWITTER_API_SECRET'])
        # we decided to follow reuters. You can put something else too =)
        query = {'screen_name': 'reuters'}
        tweets = python_tweets.get_user_timeline(**query)
        # only take recent tweets
        recent_tweets = [tweet for tweet in tweets
                         if is_recent(tweet)]   
        # format tweets
        recent_tweets = [extract_fields(tweet) for tweet in recent_tweets]
        # add sentiment to tweets
        recent_tweets = [add_sentiment_score(tweet) for tweet in recent_tweets]
        # create a filename with datetime timestamp
        now_str = datetime.now(tz=pytz.UTC).strftime('%d-%m-%Y-%H:%M:%S')
        filename = f'{now_str}.json'
        output_path_file = f'/tmp/{filename}'
        # in lambda files need to be dumped into /tmp folder
        with open(output_path_file, 'w') as fout:
            tweets_to_save = [convert_timestamp_to_int(tweet)
                              for tweet in recent_tweets]
            json.dump(tweets_to_save , fout)
        upload_file_to_s3(local_file_name=output_path_file,
                          bucket=S3_BUCKET_NAME,
                          s3_object_name=f'raw-messages/{filename}')

        tweets_df = pd.DataFrame(recent_tweets)
        conn = get_db_connection()
        insert_data_in_db(df=tweets_df, conn=conn, table_name='tweets_analytics')
    except Exception as e:
        logging.exception('Exception occured \n')
    # add_messages_to_db(df=tweets_df, conn=conn)
    print('Lambda executed succesfully!')


if __name__ == "__main__":
    lambda_handler({}, {})