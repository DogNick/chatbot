# coding=utf8

#a1. import sys
import hashlib
import json
import time
import logging
#a2. import thirdparty
from bs4 import BeautifulSoup
from lxml import etree
import redis
import tornado
from tornado import gen
import traceback
#a3. import applicaiton
from wechat_conf import Config, redis_pool_afanti
from tool import encode_multipart_formdata
from tool import post_news_msg
#b. env & global
REDIS_KEY_TIMEOUT = 604800
SOGOU_TOKEN = "afanti_sogou_20170612"


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")


def save_html_content(url, content):
	try:
		rc = redis.Redis(connection_pool = redis_pool_afanti)
		rc.set(url, content)
		return rc.expire(url, REDIS_KEY_TIMEOUT)
	except Exception, e:
		exclog.error("\n%s" % (traceback.format_exc(e)))
		return None


def get_html_content(url):
	try:
		rc = redis.Redis(connection_pool = redis_pool_afanti)
		return rc.get(url)
	except Exception, e:
		exclog.error("\n%s" % (traceback.format_exc(e)))
		return None


@tornado.gen.coroutine
def get_afanti_by_image(picurl, callback=None):
	req = tornado.httpclient.HTTPRequest(picurl, method="GET", headers={"Content-Type":"application/json,text/json"})
	http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=2.0, connect_timeout=1.0))
	res = yield http_client.fetch(req)

	ts = int(time.time())

	plain = "%s|%s" % (SOGOU_TOKEN, ts)
	cipher = hashlib.sha1(plain.encode("utf-8")).hexdigest()
	auth_info = "%s|%s" % (cipher, ts)
	content_type, body = encode_multipart_formdata([("auth_info", auth_info)], [("pic", "pic", bytes(res.body))])

	url = "https://se.afanti100.com/sogou/search/"
	req = tornado.httpclient.HTTPRequest(url, method="POST", headers={"Content-Type": content_type, 'content-length': str(len(body))}, body=body, validate_cert=True)
	http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=3.2, connect_timeout=1.0))
	t1 = time.time()
	res = yield http_client.fetch(req)
	detlog.info('AFANTI TIME : %.2f' % ((time.time() - t1) * 1000))
	res = json.loads(res.body)
	answer_html = res["data"]["answer_html"]
	subject = res["data"]["subject"]

	if not answer_html or subject != u'数学':
		raise gen.Return((False, '', '', ''))

	soup = BeautifulSoup(answer_html, "lxml")

	notice_str = '''
	<div id="qrcode-container">
		<div id="qrcode-wrapper">
			<img id="qrcode-img" src="http://h5.search.sogou.com/qrcode_for_sogouwangzai_258.jpg">
			<div id="qrcode-instruction">长按二维码 关注搜狗汪仔</div>
		</div>
		<div id="qrcode-tip">*搜题结果仅供参考，不得作为升学、考试等的依据。</div>
	</div>
	'''

	notice_div = BeautifulSoup(notice_str)

	soup.find_all("meta")[-1].extract()
	soup.find("title").string.replace_with("参考答案")
	soup.find(id="qrcode-container").replace_with(notice_div)
	new_answer_html = str(soup)

	pageid = hashlib.sha1(new_answer_html).hexdigest()
	answer_url = "http://page.h5.search.sogou.com/?pageid=" + pageid
	save_html_content(pageid, new_answer_html)

	tree = etree.HTML(answer_html)

	title = u"参考答案"
	snipet = soup.find_all("div", {"class":"content clearfix"})[0].get_text().strip()

	raise gen.Return((True, answer_url, title, snipet))
