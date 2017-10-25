# coding=utf8

#a1. import sys
import datetime
import json
import logging
import mimetypes
import os
import random
import re
import redis
import sys
import traceback

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(curr_dir, '..'))

#a2. import thirdparty
import requests
import tornado
import tornado.gen
from tornado import gen
import urllib

#a3. import application
from wechat_conf import Config, redis_pool_token


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")

'''
	generate 10 digit random number
'''
def get_random_numbers():
	numbers = ''
	for _ in range(20):
		numbers += str(int(random.random()*10))
	return numbers


'''
	THIS FUNCTION IS SUPPOSED TO BE 100% RELIABLE
	NEVER UPDATE ACCESS_TOKEN WITHOUT UPDATING REDIS!!!
'''
@tornado.gen.coroutine
def get_access_token(account):
	red = redis.Redis(connection_pool = redis_pool_token)
	token = red.get(account + ':access_token')

	# in case expired from redis
	if token == None:
		token = yield update_access_token(account)

	raise gen.Return(token)


'''
	THIS FUNCTION IS ALSO SUPPOSED TO BE 100% RELIABLE
	NEVER UPDATE ACCESS_TOKEN WITHOUT UPDATING REDIS!!!
'''
@tornado.gen.coroutine
def update_access_token(account):

	url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s' % (Config.ACCOUNT_INFO[account]['APPID'], Config.ACCOUNT_INFO[account]['SECRET'])

	req = tornado.httpclient.HTTPRequest(url, method="GET", headers=None, body=None)
	http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=1,connect_timeout=1))
	r = yield http_client.fetch(req)
	token = Config.token_p.findall(r.body)[0]
	red = redis.Redis(connection_pool = redis_pool_token)
	red.set(account + ':access_token', token)
	red.expire(account + ':access_token', 7000) # a little less than 7200
	raise gen.Return(token)

'''
	download an picture by url, and push to wechat as tempory material
'''
@tornado.gen.coroutine
def url2mediaId(picurl, account):
	# step1: download picture
	pic_file = '/search/odin/chatbot/trunk/cache/'+ get_random_numbers()+'.jpg'
	urllib.urlretrieve(picurl, pic_file)

	# step2: push to wechat
	token = yield get_access_token(account)
	url = 'http://file.api.weixin.qq.com/cgi-bin/media/upload?access_token=%s&type=image' % token
	files = [('image', pic_file, open(pic_file, 'rb').read())]
	content_type, body = encode_multipart_formdata([], files)
	headers = {"Content-Type": content_type, 'content-length': str(len(body))}
	req = tornado.httpclient.HTTPRequest(url, "POST", headers=headers, body=body, validate_cert=False)
	http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=2,connect_timeout=1))
	r = yield http_client.fetch(req)

	# TODO CHECK: THIS SHOULD NOT HAPPEN, or make try except
	if r.body.find('42001') != -1:
		update_access_token(account)
		req = tornado.httpclient.HTTPRequest(url, "POST", headers=headers, body=body, validate_cert=False)
		http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=2,connect_timeout=1))
		r = yield http_client.fetch(req)

	try:
		detlog.info("+++++++++++++++++++++++++++++++++++ r.body %s " % r.body)
		mediaId = Config.mediaId_p.findall(r.body)[0].encode('utf8') # do this for logging
	except Exception, e:
		exclog.error("\n%s" % traceback.format_exc(e))
		mediaId = ""

	# mediaId maybe '' at many places, so do not use bool
	raise gen.Return(mediaId)


'''
	a non tornado version of getting token / update
'''
def get_access_token_v2(account):
	red = redis.Redis(connection_pool = redis_pool_token)
	token = red.get(account + ':access_token')
	if token == None:
		url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s' % (Config.ACCOUNT_INFO[account]['APPID'], Config.ACCOUNT_INFO[account]['SECRET'])
		r = requests.get(url, verify = False)
		token = Config.token_p.findall(r.text)[0]
	return token

'''
	Get permnent image mediaIds, for ONCE WHEN STARTS
'''
def get_image_mediaIds(account):
	try:
		token = get_access_token_v2(account)
		# get permnent materials
		data = json.dumps({'type':'image','offset':0,'count':1000}) # must use json.dumps()
		url = "https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=%s" % token
		r = requests.post(url, data = data, verify = False)
		lst = Config.mediaId_p.findall(r.text)
		lst = map(lambda x : x.encode('utf-8'), lst) # do this for logging
		return lst
	except Exception, e:
		exclog.error("\n%s" % traceback.format_exc(e))
		return []

@tornado.gen.coroutine
def post_news_msg(openid, answer_url, title, description, glovar):

	data={
		"touser": "",
		"msgtype":"news",
		"news":{
			"articles":[
				{
					"title":"title_position",
					"description":"description_position",
					"url":"",
					#"picurl":""
				}
			]
		}
	}
	news_url = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=%s"

	if openid == "":
		detlog.info("[Post news msg Error]: openid can not be empty!")
		return

	data["touser"] = openid
	data["news"]["articles"][0]["url"] = answer_url

	access_token = yield get_access_token(glovar.account)
	data = json.dumps(data)
	data = data.replace("title_position", title).replace("description_position", description)

	req = tornado.httpclient.HTTPRequest(news_url % access_token, method="POST", headers={"Content-Type":"application/json,text/json"}, body=data.encode("utf-8"))
	http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=2.0, connect_timeout=2.0))
	res = yield http_client.fetch(req)

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        filename = filename.encode("utf8")
        L.append('--' + BOUNDARY)
        L.append(
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (
                key, filename
            )
        )
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
