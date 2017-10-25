#coding=utf8
import re
import sys
import pdb
import time
import json
import urllib
import random
import traceback
sys.path.append('../')
sys.path.append('../../')
sys.path.append('../lib')
sys.path.append('../../lib')
sys.path.append('../conf')
sys.path.append('../../conf')
import gevent
import requests
from rdd import RDD
from trie import TagMake
import gevent.monkey
from gevent import monkey
from gevent.pool import Group
from gevent.event import Event
from gevent.event import AsyncResult
from config import Config
monkey.patch_all(httplib=False)


curr_dir = os.path.dirname(os.path.abspath(__file__))
block_turing_words = RDD.TextFile(os.path.join(curr_dir, Config.TURING_BLOCK_WORD)).map(lambda x:x.strip().decode('utf8')).collect()
block_turing_tree = TagMake()
[block_turing_tree.add_tag(word) for word in block_turing_words]

api_keys = RDD.TextFile(Config.TURING_APIKEY).map(lambda x:x.split('\t')[0]).collect()



p_content = re.compile('<Content><!\[CDATA\[(.+)\]\]></Content>')
def sendmsg_turing(msg):
	url = "http://www.tuling123.com/api/product_exper/chat.jhtml"
	data = "info=%s&userid=eac1daa1-2dce-4058-baf2-053c0538e213&_xsrf="%(urllib.quote(msg))
	cookie = "JSESSIONID=BEB608CF36CDE392164964A5FECD393E;CNZZDATA1000214860=801809099-1473240285-%7C1473240285"

	headers = {"Host": "www.tuling123.com","Connection": "keep-alive", "Content-Length": len(data),"Accept": "application/xml, text/xml, */*; q=0.01", "Origin": "http://www.tuling123.com", "X-Requested-With": "XMLHttpRequest","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": "http://www.tuling123.com/experience/exp_virtual_robot.jhtml?nav=exp", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4", "Cookie":cookie, "DNT": 1}
	try:
		response = requests.post(url, headers=headers, data=data, timeout=3)
		if response:
			results = p_content.findall(response.text)
			return 100000, results[0].encode('utf8')
		return 0, ''
	except Exception, e:
		print(traceback.format_exc())
		return -1, ''




def sendmsg_turing2(msg, uid):

	# test api keys
	#payload = {'key' : '33735667432943e0a6ccfa3254129cf4', 'info' : msg, 'userid' : uid}
	#payload = {'key' : '53e367ddcbee45dca528da1d3b880a60', 'info' : msg, 'userid' : uid}

	# random from api keys pool

	code = 0
	debug_json = {'from':'turing'}


	m = re.sub(r'\w+', 'W', msg)
	if len(m.decode('utf8')) > 12:
		debug_json['status'] = 'long query'
		return None, json.dumps(debug_json)

	TRY_NUM = 3
	flags = [0] * TRY_NUM
	t0 = time.time()
	res = AsyncResult()
    # def a method to be spawned
	def go(i):
		payload = {'key' : api_keys[random.randint(0, len(api_keys) -1)], 'info' : msg, 'userid' : uid}
		url = "http://www.tuling123.com/openapi/api"
		t0 = time.time()
		try:
			proxies = {'http':'http://adslspider%02d.web.zw.vm.sogou-op.org:8080' % random.randint(1, 16)}
			response = requests.post(url, data=payload, timeout=(0.6, 0.7), proxies=proxies)
			res.set(response)
			flags[i] = 1
#print ("adsl %d succeeded!! time %.4f," % (i, (time.time() - t0)))
		except Exception, e:
			flags[i] = 1
#			print (traceback.format_exc())
			if flags == [1] * TRY_NUM:
				res.set(None)
#			print ("adsl %d exception! time %.4f" % (i, (time.time() - t0)))

		return


	glst = [gevent.spawn(go, i) for i in range(TRY_NUM)]
#	print ("main begin wait ..%.4f" % time.time())
	t1 = time.time()
	response = res.get()
#	print "main wait time,  %.4f" % (time.time() - t1)

	if not response:
		debug_json['status'] = 'err: %d adsl trys all failed' % TRY_NUM
		return None, json.dumps(debug_json)

	j = json.loads(response.text)
	code = j.get('code')
	if code == 100000:
		text = j.get('text')
		if len(block_turing_tree.make(text)) > 0:
			debug_json['status'] = 'has filter word'
			return None, json.dumps(debug_json)
		else:
			return text, json.dumps(debug_json)
	else:
		debug_json['status'] = 'response not text'
		return None, json.dumps(debug_json)



if __name__ == "__main__":
	while True:
		msg = raw_input('say: ')
		text, debug_json_str = sendmsg_turing2(msg, '1001')
		if text:
			print text.encode('utf8')
		else:
			print "None"
