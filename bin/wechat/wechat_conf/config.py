#coding=utf8

#a1. import sys
import re

#a2. import thirdparty

#a3. import application

#b. env & global

class GloVar():
	def __init__(self, account):
		self.account = account 
		self.random_image_mediaIds = []

class Config():
	
	ACCOUNT_INFO = {
					'sogouwangzai' : {'APPID' : 'wx1dd290b0afdc29dc', 'SECRET' : '41ed6971fb64a968adc3fd195b2d7b1c'}, 
					'beitawang' : {'APPID' : 'wx0fddf639f7ae19fd', 'SECRET' : '4a9948aeeeb99215e1e707d87eedbaf6'},
					'afawang' : {'APPID' : '', 'SECRET' : ''}, 
					'sosohelper' : {'APPID' : '', 'SECRET' : ''}, 
					'dognick': {'APPID': 'wxbcc46363867e4548', 'SECRET': '738f6c600a079233b03746197e59ca32'},
					'jstvyzdd': {'APPID': 'wx8a6ee8998bb9d211', 'SECRET': '5f880db7918393ea137941bc460ca801'},
					#'dognick': {'APPID': '', 'SECRET': ''}
				}
	BROKER_ADDR = 'http://wechat.chatbot.sogou/'
	TIMEOUT = 3

	'''
		parsing
	'''
	EMOJI_ADDR = 'data/emoji_list'
	EMOJI_WX_WX = 'data/emoji_wx_wx'
	EMOJI_WX_SB	= 'data/emoji_wx_sb'
	EMOJI_WX_ALL = 'data/emoji_wx_all'
	EMOJI_WX_OT = 'data/emoji_wx_ot'
	EMOJI_REPLIES_ADDR = 'data/emoji_replies'
	unsupported_msg_set = set(['【收到不支持的消息类型，暂无法显示】', '【收到不支援的訊息類型，無法顯示】', '[Unsupported Message]', '[Unsupported message]'])

	'''
		response
	'''
	DEFAULT_RET = '/::)'
	DEFAULT_ERROR_RET = '/::!'
	DEFAULT_UNKNOWN_RET = '???'
	WELCOME_RET_LIST = ['你终于来啦/::)'] # welcome
	FREE_RET_LIST = ['/::)', '/::$', '/::P', '/::D', '/::d', '/:,@P'] # @deprecated random emojis
	LOCATION_RET_LIST = ['这是哪里呀', '你在这儿?', '你现在在这儿?'] # for user proactively shared location (not passive reported LOCATION)

	'''
		redis
	'''
	WECHAT_REDIS = ('b.redis.sogou', 1765, '0', 'chatbot')


	'''
		thirdparty
	'''
	XIAOBING_ADDR='http://doge.sogou-inc.com:9500/xiaobing?'
	TURING_ADDR='http://doge.sogou-inc.com:9500/turing?'

	'''
		game: scan qrcode(with param), send game result webpage
	'''
	GAME_RESULT_URL = 'http://sogou.com?scene_id=%'
	GAME_RESULT_TITLE = 'sogou'
	GAME_RESULT_SNIPIT = 'sogou'

	'''
		regex
	'''
	content_p = re.compile('<Content><!\[CDATA\[(.*)\]\]></Content>')
	event_p = re.compile('<Event><!\[CDATA\[(.*)\]\]></Event>')
	from_user_p = re.compile('<FromUserName><!\[CDATA\[(.*)\]\]></FromUserName>')
	mediaId_p = re.compile('media_id":"(.*?)"')
	msg_type_p = re.compile('<MsgType><!\[CDATA\[(.*)\]\]></MsgType>')
	picurl_p = re.compile('<PicUrl><!\[CDATA\[(.*)\]\]></PicUrl>')
	recognition_p = re.compile('<Recognition><!\[CDATA\[(.*)\]\]></Recognition>')
	token_p = re.compile('access_token":"(.*?)"') 
	to_user_p = re.compile('<ToUserName><!\[CDATA\[(.*)\]\]></ToUserName>')
	msgid_p = re.compile('<MsgId>(.*)</MsgId>')
	create_time_p = re.compile('<CreateTime>(.*)</CreateTime>')
	latitude_p = re.compile('<Latitude>(.*)</Latitude>')
	longitude_p = re.compile('<Longitude>(.*)</Longitude>')
	event_key_p = re.compile('<EventKey><!\[CDATA\[(.*)\]\]></EventKey>')

	'''
		xml or logging templates
	'''
	text_reply_template = """<xml><ToUserName><![CDATA[%s]]></ToUserName>
<FromUserName><![CDATA[%s]]></FromUserName>
<CreateTime>%s</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[%s]]></Content>
</xml>"""

	image_reply_template = """<xml><ToUserName><![CDATA[%s]]></ToUserName>
<FromUserName><![CDATA[%s]]></FromUserName>
<CreateTime>%s</CreateTime>
<MsgType><![CDATA[image]]></MsgType>
<Image>
<MediaId><![CDATA[%s]]></MediaId>
</Image>
</xml>"""

	log_template = """
server_time:
%s
wechat_time:
%s
response_time:
%s
request_xml:
%s
response_xml:
%s
handle_type:
%s
wechat_uri:
%s"""

	xiaoe_request_template1 = """<xml><ToUserName><![CDATA[xiao-e]]></ToUserName>
<FromUserName><![CDATA[sogouwangzai]]></FromUserName>
<Gender><![CDATA[%s]]></Gender>
<CreateTime>0000000000</CreateTime>
<MsgType><![CDATA[image]]></MsgType>
<PicUrl><![CDATA[%s]]></PicUrl>
<MsgId>0000000000000000000</MsgId>
<MediaId><![CDATA[dummy]]></MediaId>
</xml>"""

	xiaoe_request_template2 = """<xml><ToUserName><![CDATA[xiao-e]]></ToUserName>
<FromUserName><![CDATA[sogouwangzai]]></FromUserName>
<Gender><![CDATA[%s]]></Gender>
<CreateTime>0000000000</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[%s]]></Content>
<MsgId>0000000000000000000</MsgId>
</xml>"""
