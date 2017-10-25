#a1. import sys
import logging
import os
import re
import sys
import traceback

curr_dir = os.path.dirname(os.path.abspath(__file__))

#a2. import thirdparty
import requests
import tornado.gen
from tornado import gen
from trie import TagMake

#a3. import application
from wechat_conf import Config
from tool import url2mediaId

detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")

#b. env & global
picture_intent_tree = TagMake()
for line in open(os.path.join(os.path.join(curr_dir, 'data'), 'picture_intents')):
	picture_intent_tree.add_tag(line.strip())

def match_picture_intent(query):
	return len(picture_intent_tree.make(query)) > 0

@tornado.gen.coroutine
def get_image_by_image(gender, picurl, account):
	detlog.info('[EXT]' + ' call by url %s' % picurl)
	xml = Config.xiaoe_request_template1 % (gender, picurl)
	try:
		req = tornado.httpclient.HTTPRequest("http://weixin.pic.sogou.com/weixin/", method="POST", headers=None, body=xml)
		http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=3.5,connect_timeout=1))
		r = yield http_client.fetch(req)
		ret_picurl = Config.content_p.findall(r.body)[0]
		if ret_picurl.find('http') != 0:
			mediaId = ''
		else:
			mediaId = yield url2mediaId(ret_picurl, account)
			detlog.info('[EXT] got picture')
	except Exception, e:
		exclog.error("\n%s" % traceback.format_exc(e))
		mediaId = ''
	raise gen.Return(mediaId)


@tornado.gen.coroutine
def get_image_by_text(gender, text, account):
	detlog.info('[EXT]' + ' call by text %s' % text)
	xml = Config.xiaoe_request_template2 % (gender, text)

	try:
		req = tornado.httpclient.HTTPRequest("http://weixin.pic.sogou.com/weixin/", method="POST", headers=None, body=xml)
		http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=3,connect_timeout=1))
		r = yield http_client.fetch(req)
		ret_picurl = Config.content_p.findall(r.body)[0]
		if ret_picurl.find('http') != 0:
			mediaId = ''
		else:
			mediaId = yield url2mediaId(ret_picurl, account)
			detlog.info('[EXT] got picture')
	except Exception, e:
		exclog.error("\n%s" % traceback.format_exc(e))
		mediaId = ''
	raise gen.Return(mediaId)


@tornado.gen.coroutine
def xiaoe(self, glovar, callback=None):
	#1 call xiaoe
	self.reply_mediaId = yield get_image_by_image('', self.picurl, glovar.account)
	if self.reply_mediaId == '':
		self.reply_mediaId = random.choice(glovar.random_image_mediaIds)
	raise gen.Return("")
