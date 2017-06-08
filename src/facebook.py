#!/usr/bin/python3
"""
Planbot's Facebook application. Handles requests and responses through the
Wit and Facebook Graph APIs.
"""

import os
import logging

import requests
from bottle import Bottle, request, debug

from engine import Engine

# set environmental variables
FB_PAGE_TOKEN = os.environ.get('FB_PAGE_TOKEN')
FB_VERIFY_TOKEN = os.environ.get('FB_VERIFY_TOKEN')

# setup Bottle Server
debug(True)
app = application = Bottle()

# setup logging
logging.basicConfig(level=logging.INFO)


@app.get('/facebook')
def messenger_webhook():
    verify_token = request.query.get('hub.verify_token')
    if verify_token == FB_VERIFY_TOKEN:
        challenge = request.query.get('hub.challenge')
        return challenge
    else:
        return 'Invalid Request or Verification Token'


@app.post('/facebook')
def messenger_post():
    data = request.json
    responses = []
    if data['object'] == 'page':
        for entry in data['entry']:
            messages = entry['messaging']
            if messages[0]:
                message = messages[0]
                fb_id = message['sender']['id']
                if message.get('message'):
                    if message.get('attachments'):
                        attachment = messsage['message']['attachments'][0]
                        if attachment['title'] == 'Pinned Location':
                            long = attachment['coordinates']['long']
                            lat = attachment['coordinates']['lat']
                            text = geo_convert(longitude=long, latitude=lat)
                        else:
                            text = 'NO_PAYLOAD'
                    else:
                        text = message['message']['text']
                elif message.get('postback'):
                    text = message['postback']['payload']

                logging.info('Message received: {}'.format(text))
                responses.append(text)
    else:
        return 'Received Different Event'

    if responses:
        text = responses[0]
    else:
        text = 'NO_PAYLOAD'

    bot = Engine()
    for response in bot.response(user=fb_id, message=text):
        sender_action(fb_id)
        send(response)

    return None


def sender_action(sender_id):
    data = {'recipient': {'id': sender_id}, 'sender_action': 'typing_on'}
    qs = 'access_token=' + FB_PAGE_TOKEN
    resp = requests.post('https://graph.facebook.com/v2.9/me/messages?' + qs,
                         json=data)

    return resp.content


def send(response):
    fb_id = response['id']
    text = response['text']
    quickreplies = cards = None

    # check for quickreplies
    if response.get('quickreplies'):
        quickreplies = format_qr(response['quickreplies'])

    # check for urls
    if text.startswith('http'):
        urls = text.split()
        titles = response['title']
        cards = template(titles, urls)

    fb_message(fb_id, text, quickreplies, cards)
    return None


def fb_message(sender_id, text, quickreplies, cards):
    data = {'recipient': {'id': sender_id}}

    data['message'] = cards if cards \
        else{'text': text, 'quick_replies': quickreplies} if quickreplies \
        else {'text': text}

    # logging.info('response = {}'.format(data))

    qs = 'access_token=' + FB_PAGE_TOKEN
    resp = requests.post('https://graph.facebook.com/v2.9/me/messages?' + qs,
                         json=data)

    return resp.content


def format_qr(quickreplies):
    return [{
        'title': qr,
        'content_type': 'text',
        'payload': 'empty'}
            for qr in quickreplies]


def template(titles, urls):
    button_titles = ['Download' if url.endswith('pdf') else 'View'
                     for url in urls]

    elements = [{
        'title': titles[i],
        'default_action': {
            'type': 'web_url',
            'url': urls[i]},
        'buttons': [{
            'type': 'web_url',
            'url': urls[i],
            'title': button_titles[i]}]}
             for i in range(len(titles))]

    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": elements}}}


def geo_convert(longitude=None, latitude=None):
    url = 'https://api.postcodes.io/postcodes?lon={}&lat={}'
    res = requests.get(url).json()
    try:
        text = res['result'][0]['admin_district']
    except KeyError:
        logging.info('Invalid coordinates: long={}; lat={}'.format(
            longitude, latitude))
        text = 'NO_PAYLOAD'
    return text
