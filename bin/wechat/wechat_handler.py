#coding=utf8

#a1. import sys
import datetime
import json
import logging
import os
import random
import re
import sys
import time
import traceback

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, '.'))
sys.path.append(os.path.join(curr_dir, '../'))
sys.path.append(os.path.join(curr_dir, '../common'))
sys.path.append(os.path.join(curr_dir, '../../lib'))

#a2. import thirdparty
import hashlib
import redis
import tornado
from tornado import gen
from tornado.gen import Future
import tornado.web

#a3. import application
from afanti_acc import get_afanti_by_image
from chathub import FutureHandler
from schedules import *
from emoji_tool import clean_emoji_in_query
from tool import add_user_info, get_image_mediaIds, get_access_token, post_news_msg, update_user_location, get_user_cmd, put_user_cmd
from wechat_conf import Config, GloVar
from xiaoe_acc import get_image_by_image, get_image_by_text, match_picture_intent

#b. env & global
reload(sys)
sys.setdefaultencoding("utf-8")
detlog = logging.getLogger("details")
onlinelog = logging.getLogger("online")
exclog = logging.getLogger("exception")


class Any(Future):
	def __init__(self, futures):
		super(Any, self).__init__()
		for future in futures:
			future.add_done_callback(self.done_callback)
	def done_callback(self, future):
		self.set_result(future)


class WechatHandler(FutureHandler):
	def initialize(self, conf, schedules, cache, session_manager):
		super(WechatHandler, self).initialize(conf, schedules, cache, session_manager)

	def set_default_headers(self):
		self.set_header('Access-Control-Allow-Origin', "*")

	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def post(self):
		detlog.info("\n\n************************* new conversation begin *************************")
		detlog.info("[wechat] [BEGIN] [REQUEST] [%s]" % (self.request.uri))
		data = self.request.body
		try:
			self.rid = Config.msgid_p.findall(data)[0]
		except:
			self.rid = 'subscribe_request_without_msgid'
		self.to_user = Config.to_user_p.findall(data)[0]
		self.from_user = Config.from_user_p.findall(data)[0]
		self.msg_type = Config.msg_type_p.findall(data)[0]
		self.create_time = Config.create_time_p.findall(data)[0]

		if self.msg_type == 'text':
			temp_data = data.replace('\n', '')
			self.content = Config.content_p.findall(temp_data)[0]
		elif self.msg_type == 'voice':
			self.content = Config.recognition_p.findall(data)[0]
		else:
			self.content = ''

		if self.msg_type == 'event':
			self.event = Config.event_p.findall(data)[0]
			try:
				self.event_key = Config.event_key_p.findall(data)[0]
			except:
				self.event_key = ''
			if self.event == 'LOCATION':
				self.latitude = Config.latitude_p.findall(data)[0]
				self.longitude = Config.longitude_p.findall(data)[0]
			else:
				self.latitude = ''
				self.longitude = ''
		else:
			self.event = ''

		if self.msg_type == 'image':
			self.picurl = Config.picurl_p.findall(data)[0]

		self.is_unsupported_text  = self.msg_type == 'text' and self.content in Config.unsupported_msg_set

		self.reply_msg_type = ''
		self.reply_content = ''
		self.handle_type = ''
		reply_mediaId = ''

		log = {}
		log['server_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
		log['wechat_uri'] = self.request.uri.encode('utf8')
		log['request_xml'] = data
		try:
			yield self.handle_wechat()
			result = self.reply_formatter()
		except Exception, e:
			exclog.error("\n%s" % traceback.format_exc(e))
			result = Config.text_reply_template % (self.from_user, self.to_user, int(time.time()), "")
		self.write(result)
		log['response_xml'] = result
		log['handle_type'] = self.handle_type

		try:
			log['wechat_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(create_time_p.findall(data)[0])))
			log['response_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(create_time_p.findall(result)[0])))
		except:
			log['wechat_time'] = 'NULL'
			log['response_time'] = 'NULL'

		onlinelog.info(Config.log_template % (log['server_time'], log['wechat_time'], log['response_time'], log['request_xml'], log['response_xml'], log['handle_type'], log['wechat_uri']))
		onlinelog.info('neat\t%s\t%s\t%s\t%s' % (log['response_time'], self.content, self.handle_type, self.reply_content.replace('\n', '')))
		onlinelog.info('--------------------')
		self.finish()


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		if len(self.request.arguments) > 3:
			token = 'weixin'
			signature = self.get_argument('signature', '')
			timestamp = self.get_argument('timestamp', '')
			nonce = self.get_argument('nonce')
			echostr = self.get_argument('echostr')
			temparr = []
			temparr.append(token)
			temparr.append(timestamp)
			temparr.append(nonce)
			temparr.sort()
			newstr = ''.join(temparr)
			temp = hashlib.sha1(newstr).hexdigest()
			if signature == temp:
				self.write(echostr)
				self.finish()
				return
			else:
				self.write("error")
				self.finish()
				return


	@tornado.gen.coroutine
	def handle_wechat(self):
		if self.msg_type == 'event' and self.event == 'subscribe':
			self.reply_msg_type = 'text'
			self.reply_content = random.choice(Config.WELCOME_RET_LIST)
			self.handle_type = '订阅'
			add_user_info(self.from_user, self._glovar)

			if self.event_key.find('qrscene_') != -1:
				scene_id = self.event_key.split('qrscene_')[1]
				h5_url = Config.H5_GAME_URL % scene_id
				h5_title = Config.H5_GAME_TITLE
				h5_snipet = COnfig.H5_GAME_SNIPET
				yield self.post_news_msg(self.from_user, h5_url, h5_title, h5_snipet, self._conf._glovar)
			return

		if self.msg_type == 'event' and self.event == 'unsubscribe':
			self.reply_msg_type = 'success'
			self.handle_type = '取消订阅'
			return

		if self.msg_type == 'event' and self.event == 'SCAN':
			self.reply_msg_type = 'success'
			self.handle_type = '扫描带参二维码'
			scene_id = self.event_key

			h5_url = Config.H5_GAME_URL % scene_id
			h5_title = Config.H5_GAME_TITLE
			h5_snipet = COnfig.H5_GAME_SNIPET

			yield self.post_news_msg(self.from_user, h5_url, h5_title, h5_snipet, self._conf._glovar)
			return

		if self.msg_type == 'event' and self.event == 'LOCATION':
			self.reply_msg_type = 'success'
			self.handle_type = '自动上报'
			update_user_location(self.from_user, self.latitude, self.longitude, self._conf._glovar)
			return

		if self.msg_type == 'location':
			self.reply_msg_type = 'text'
			self.reply_content = random.choice(Config.LOCATION_RET_LIST)
			self.handle_type = '位置'
			return

		if self.msg_type == 'video':
			self.reply_msg_type = 'text'
			self.reply_content = random.choice(Config.FREE_RET_LIST)
			self.handle_type = '视频'
			return

		if self.msg_type == 'link':
			self.reply_msg_type = 'text'
			self.reply_content = random.choice(Config.FREE_RET_LIST)
			self.handle_type = '链接'
			return

		if self.msg_type == 'image':

			# start xiaoe first
			xiaoe_future = gen.Task(get_image_by_image, '', self.picurl, self._conf._glovar.account)

			# try afanti
			has_afanti, answer_url, title, snipet = yield gen.Task(get_afanti_by_image, self.picurl)
			if has_afanti:
				yield post_news_msg(self.from_user, answer_url, title, snipet, self._conf._glovar)
				self.reply_msg_type = "success"
				self.handle_type = '图片-p2p-AFT'
				return

			# try xiaoe
			mediaId = yield xiaoe_future
			if mediaId != '':
				self.reply_mediaId = mediaId
				self.reply_msg_type = "image"
				self.handle_type = '图片-p2p-XE'
				return

			# default
			self.reply_mediaId = random.choice(self._conf._glovar.random_image_mediaIds)
			self.reply_msg_type = "image"
			self.handle_type = '图片-p2p-DEFAULT'
			return

		if self.is_unsupported_text:
			self.reply_msg_type = 'image'
			self.reply_mediaId = random.choice(self._conf._glovar.random_image_mediaIds)
			self.handle_type = '图片-2'
			return

		if self.msg_type != 'text' and self.msg_type != 'voice':
			self.reply_msg_type = 'success'
			self.handle_type = '未知'
			return

		if self.content == '':
			self.reply_msg_type = 'success'
			self.handle_type = '未知'
			return

		if self.handle_command():
			self.handle_type = '命令'
			return

		# filter emoji
		flag, emoji_reply, cleaned_query = clean_emoji_in_query(self.content, 'wechat')

		if flag:
			self.reply_content = emoji_reply
			self.reply_msg_type = 'text'
			self.handle_type = 'Emoji'
			return
		else:
			self.content = cleaned_query

		# judge if is a doutu
		if match_picture_intent(self.content):
			self.reply_msg_type = 'image'
			self.reply_mediaId = yield get_image_by_text('', self.content, self._conf._glovar.account)
			if self.reply_mediaId == '':
				# NOTE: compared to get_image_by_image,
				# this get_image_by_text is not supposed to be invalid
				self.reply_mediaId = random.choice(self._conf._glovar.random_image_mediaIds)
			self.handle_type = '图片-3'
			return

		self.reply_content = yield self.handle_text_msg_by_chathub(self.content.decode("utf-8"), "wechat", self.from_user)


	def handle_command(self):
		is_command = False
		if self.content == 'turnondebug' or self.content == 'turnoffdebug':
			put_user_cmd(self.from_user, self.content)
			is_command = True
		detlog.info("after put_user_cmd")
		if is_command:
			self.reply_msg_type = "text"
			self.reply_content = "switched"
		return is_command


	@tornado.gen.coroutine
	def handle_text_msg_by_chathub(self, query, source, uid):
		self.uid = uid
		self.query = query
		self.source = source
		self.debug = "0"

		query, acc_params = self.preproc(query, source, uid)
		results = yield self.do_chat(query, source, uid, acc_params)

		ret_str = results[0]["answer"].encode('utf8')
		debug_info = results[0]['debug_info']
		if len(ret_str) > 2048:
			ret_str = self.get_2048_byte_answer(ret_str)

		self.reply_msg_type = 'text'
		if 'sub_type' not in debug_info:
			self.handle_type = '无结果'
		else:
			self.handle_type = debug_info['sub_type'].encode('utf8')

		if get_user_cmd(self.from_user) == "turnondebug":
			if len(ret_str + ' ' + json.dumps(debug_info, ensure_ascii = False).encode("utf-8")) <= 2048:
				ret_str += ' ' + json.dumps(debug_info, ensure_ascii = False).encode("utf-8")
		raise gen.Return(ret_str)


	def get_2048_byte_answer(self, ret_str):
		answer_utf8 = ''
		new_line_utf8 = ''
		for ch in ret_str.decode('utf-8'):
			if ch == u'!' or ch == u'?' or ch == u' ' or ch == u'\u3002' or ch == u'\uff01' or ch == u'\uff1f' or ch == u',' or ch == u'\uff0c' or ch == u'.':
				if len((answer_utf8 + new_line_utf8)) > 2048:
					if len(answer_utf8 + '等') < 2048:
						answer_utf8 = answer_utf8 + '等'
					break
				else:
					answer_utf8 = answer_utf8 + new_line_utf8
					new_line_utf8 = ch.encode('utf-8')
			else:
				new_line_utf8 = new_line_utf8 + ch.encode('utf-8')
		return answer_utf8


	def reply_formatter(self):
		if self.reply_msg_type == '' or self.reply_msg_type == 'success':
			return 'success'

		if self.reply_msg_type == 'text':
			if self.reply_content == Config.DEFAULT_RET or self.reply_content == Config.DEFAULT_ERROR_RET or self.reply_content == Config.DEFAULT_UNKNOWN_RET:
				return "success"
			return Config.text_reply_template % (self.from_user, self.to_user, int(time.time()), self.reply_content)

		if self.reply_msg_type == 'image':
			return Config.image_reply_template % (self.from_user, self.to_user, int(time.time()), self.reply_mediaId)


	def select_results(self, acc_results, acc_status):
		ret = []
		should_cache = False
		done = False
		for result_list in acc_results:
			if not result_list:
				continue
			for res in result_list:
				if res["answer"]:
					answer = res["answer"]
					debug_info = res["debug_info"]
					ret.append({"answer":answer, "debug_info":debug_info})
					done = True
					break
			if done:
				break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default", "sub_type":"闲聊-默认"}
			ret.append({"answer":random.choice(default_answer_list), "debug_info":debug_info})
		return ret, should_cache


def make_app(global_conf, schedules, cache, session_manager, account):
	global_conf._glovar = GloVar(account)
	global_conf._glovar.random_image_mediaIds = get_image_mediaIds(account)
	app = tornado.web.Application(
		[
			(r'/weixin', WechatHandler, dict(conf=global_conf, schedules=schedules, cache=cache, session_manager=session_manager)),
		]
	)
	return app

