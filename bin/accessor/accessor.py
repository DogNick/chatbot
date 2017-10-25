#coding=utf-8
import abc
import collections
import json
import logging
import os
import pdb
import random
import re
import sys
import time
import traceback
import urllib

reload(sys)
sys.setdefaultencoding('utf-8')
curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, '../'))
sys.path.append(os.path.join(curr_dir, '../common'))
sys.path.append(os.path.join(curr_dir, '../../lib'))

import tornado.httpclient
from tornado import gen
from tornado import ioloop
from tornado.gen import multi

from config import Config


detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


@gen.coroutine
def parallel_async(async_reqs_param_list, wait_for_all=True):
	"""Do asynchronized http request in parallel
	Params:
		req_info_tuples: A list of tuples of objects required for tornado requests i.e.
			[
				("GET","http://a.b:1000/?c=1&d=2", None, header),
				("POST","http://e.f:1001/z", {"data":"aaa"}, header),
				("GET","http://g.h:1002/?j=5", None, None)
			]
	Returns:
		A list of responses in form of..
	Raise:
		params errors
	"""
	# Do some check, maybe more..
	request_futures = []
	for each in async_reqs_param_list:
		if isinstance(each, AsyncReqsParam):
			if not isinstance(each._method, str):
				raise TypeError(
					"Need string type for http method but got '%s'" % type(each._method))
			if not isinstance(each._url, str):
				raise TypeError(
					"Need string type for http url description but got '%s'" % type(each._url))
			if each._method != "GET" and each._method != "POST":
				raise ValueError(
					"Only 'GET' or 'POST' is allowed for method but got '%s'" % each.method)
			req = tornado.httpclient.HTTPRequest(each._url, method=each._method, headers=each._headers, body=each._body)
			http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True,
				defaults=dict(request_timeout=each._timeout,connect_timeout=each._timeout))
			request_futures.append(http_client.fetch(req))
		else:
			raise TypeError(
				"Require object of class 'AsyncReqsParam' for each of async_reqs_param_list but got" % str(each))
	ret = []
	wait_iterator = gen.WaitIterator(*request_futures)
	while not wait_iterator.done():
		try:
			result = yield wait_iterator.next()
			idx = wait_iterator.current_index
			ret.append((result.body, {"id":idx, "info":"done"}))
			if not wait_for_all:
				break
		except Exception, e:
			idx = wait_iterator.current_index
			exclog.info("{0} from future at {1}, {2}".format(e, idx, async_reqs_param_list[idx].to_json()))
			ret.append((None, {"id":idx, "info":str(e)}))
		finally:
			pass
	raise gen.Return(ret)


class AsyncReqsParam(object):
	def __init__(self, method, url, body=None, headers=None, timeout=3):
		self._method = method
		self._url = url
		self._body = body
		self._headers = headers
		self._timeout = timeout
	def to_json(self):
		return {"method":self._method, "url":self._url, "body":self._body, "timeout":self._timeout}

class Accessor(object):
	_rsc = None
	_conf = None

	# Resource class with accessor-specific heavy resources packed in it
	# Overwrite init() to do accesor-specific heavy resources loading
	class Resource(object):
		def __init__(self, conf):
			self._conf = conf
		@abc.abstractmethod
		def init(self):
			pass

	# Each sub-class(inheritance) has only one instance of Resource
	# self.rsc() will return the unique instance
	@classmethod
	def rsc(self, conf=None):
		if self._conf == None and conf:
			self._conf = conf
		if self._rsc != None:
			return self._rsc
		else:
			self._rsc = self.Resource(self._conf)
			self._rsc.init()
			return self._rsc

	# This magic function MUST BE called by the class's children as 'super(Child, self).__init__(conf) in their __init__()s'
	def __init__(self, conf):
		self._conf = conf
		self.acc_name = self.__class__.__name__.lower()
		self.rsc(self._conf)

	@abc.abstractmethod
	def initialize(self):
		pass

	@abc.abstractmethod
	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			async_reqs_param = [
				AsyncReqsParam("GET", "http://10.141.176.103:9001/generate?query=%s" % urllib.quote("你在干嘛呢"), None, None),
				AsyncReqsParam("GET", "http://10.142.100.135:8000/?query=%s" % urllib.quote("what are you doing?"), None, None),
				AsyncReqsParam("GET", "http://10.141.176.103:9010/chaten?query=%s" % urllib.quote("how old are you"), None, None)
			]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = [(res_str, debug_info)]
					rets.extend(ret_list)
		except Exception, e:
			debug_info["status"] = "error, " + str(e)
			exclog.error('\n%s' % (traceback.format_exc(e)))
		if rets == []:
			rets = [(None, debug_info)]
		raise gen.Return(rets)

	@abc.abstractmethod
	@gen.coroutine
	def test(self):
		detlog.info("accessor test")
		results = yield self.run(query="", params={})

	def __call__(self):
		detlog.setLevel(logging.INFO)
		exclog.setLevel(logging.INFO)
		detlog.propagate = False
		exclog.propagate = False
		sh1 = logging.StreamHandler(stream=None)
		sh2 = logging.StreamHandler(stream=None)
		sh1.setLevel(logging.INFO)
		sh2.setLevel(logging.INFO)
		formatter1 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s')
		formatter2 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s')
		sh1.setFormatter(formatter1)
		sh2.setFormatter(formatter2)
		detlog.addHandler(sh1)
		exclog.addHandler(sh2)
		self.initialize()
		ioloop.IOLoop.instance().run_sync(self.test)


if __name__ == "__main__":
	conf = Config("dev", True, "develop")
	acc = Accessor(conf)
	acc()
