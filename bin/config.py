#coding=utf-8
import os
import random
from tornado.options import define

define('mode',default='dev',help='[bj,gd,dev]',type=bytes)
define('log_verbose',default=False,help='[logging strategy]',type=bool)
define('env',default='develop', help='environment set',type=bytes)

class Config():
	def __init__(self, mode, verbose, env="test"):
		self._mode = mode
		self._verbose = verbose
		self._env = env

	@property
	def HTTP_GENERATE(self):
		if self._mode == 'bj' or self._mode == 'gd':
			return 'http://generate.chatbot.sogou/generate' #
		if self._mode == 'dev':
			return 'http://10.141.104.69:9000/generate' # TODO what is the offline one

	@property
	def HTTP_RETRIEVE(self):
		return 'http://10.142.100.135:5045'

	@property
	def HTTP_WHITELIST(self):
		if self._mode == 'bj' or self._mode == 'gd':
			return 'http://whitelist.chatbot.sogou' # only BJ now. # TODO ask for GD E2 to deploy
		if self._mode == 'dev':
			return 'http://10.134.96.69:5335'

	@property
	def HTTP_POEM(self):
		if self._mode == 'bj':
			return 'http://bj.poem.chatbot.sogou'
		if self._mode == 'gd':
			return 'http://gd.poem.chatbot.sogou'
		if self._mode == 'dev':
			return 'http://dev.poem.chatbot.sogou'

	@property
	def HTTP_YYZS(self):
		if self._mode == 'bj':
			return 'http://bj.yyzs.chatbot.sogou'
		if self._mode == 'gd':
			return 'http://gd.yyzs.chatbot.sogou'
		if self._mode == 'dev':
			return 'http://dev.yyzs.chatbot.sogou'

	@property
	def HTTP_TRANSLATE(self):
		if self._mode == 'bj' or self._mode == 'gd':
			return 'http://gpu.fanyi.sogou/alltrans_json' # only BJ now.
		if self._mode == 'dev':
			return 'http://10.142.73.41:12200/alltrans_json'

	@property
	def HTTP_WEB_SEARCH(self):
		if self._mode == 'bj':
			return 'http://resinhub%02d.web.%s.ted:5555' % (random.randint(1, 15), random.choice(['djt', '1.djt']))
		if self._mode == 'gd':
			return 'http://resinhub%02d.web.%s.ted:5555' % (random.randint(1, 15), random.choice(['gd', '1.gd']))
		if self._mode == 'dev':
			return 'http://resinhub%02d.web.%s.ted:5555' % (random.randint(1, 15), '1.tc')

	@property
	def HTTP_YAOTING(self):
		if self._mode == 'bj':
			return random.choice(['http://cache03.wenda.tc.ted:5555', 'http://cache04.wenda.tc.ted:5555'])
		if self._mode == 'gd':
			return random.choice(['http://cache01.wenda.gd.ted:5555', 'http://cache02.wenda.gd.ted:5555'])
		if self._mode == 'dev':
			return random.choice(['http://cache03.wenda.tc.ted:5555', 'http://cache04.wenda.tc.ted:5555'])

	@property
	def HTTP_SKILL_LIST(self):
		if self._env == "cyy":
			return ['http://10.153.55.199:80/']
		elif self._env == "nick":
			return ['http://10.141.177.182:80/']
		else:
			return ['http://10.153.50.138:80/',
					'http://10.153.52.159:80/',
					'http://10.153.53.133:80/',
					'http://10.153.54.136:80/'
					]

	@property
	def RESPONSE_CACHE_REDIS(self):
		if self._mode == 'bj':
			return ('10.153.53.220', 9999, 0)
		if self._mode == 'gd':
			return ('10.145.55.203', 9999, 0)
		if self._mode == 'dev':
			return ('10.143.59.232', 9999, 0)

	@property
	def QQ_CALLBACK_URL(self):
		callback_port = 80
		if self._env == "online":
			callback_port = "80" 
		else:
			callback_port = "8080"
		return "http://robot.group.qq.com:%s/msg_reply/v2" % callback_port
	@property
	def TRANSLATE_URL(self):
		if env == "develop":
			ip = "10.143.43.84:5672"
		else:
			ip = "10.143.43.84:5672"
		translate_url = "http://%s/alltrans_json" % ip
		return translate_url
			

	'''
		flag
	'''
	SEARCH_DEBUG_FLAG = False			#search返回结果，True表明返回所有检索结果，False表明返回最优结果
	SEARCH_USE_UGC_ANSWER = False		#True表明search下游使用ugc数据，False表明search下游不使用ugc数据
	SEARCH_USE_RANDOM_ANSWER = False	#如果query类型为观点类，True表明根据query随机生成一个answer，False则不使用该功能

	'''
		remote addr
	'''
	TSINGHUA_QA_ADDR = 'http://10.153.10.56:5555'
	WEIMI_FAQ_ADDR = 'http://weimi.sogou:5555'
	HTTP_WEATHER = 'https://api.seniverse.com/v3/weather/daily.json'
	HTTP_HAOMATONG = 'http://10.136.37.23:55443/qn?phone=%s'
	UNIVERSAL_TIME_URL = 'http://time.tianqi.com/'
	QROBOT_URL = 'http://dm.wenwen.sogou.com/wenwen/api.php?query=%s'
	SKILL_PLATFORM_URL = 'http://10.144.103.187:9999/demo'
	INTENT_SERVER_URL = 'http://10.141.176.103:9000'

	'''
		local resources
	'''
	EMOJI_LABEL_ADDR = '../../data/emoji_data/emotion_label'

	MATCH_THREDSHELD = 0.8
	WAP_FILTER_TITLE = '../../data/yybb/filter_words'
	WAP_HTML_SYMBOL = '../../data/lizhi/html_symbol'

	USER_LAST_FROM = ('a.redis.sogou', 1965, 0, 'chatbot')				#存放用户上一次的from

	'''
		deprecated
	BROADCAST_WEBKIT_ADDRESS = '10.136.122.201:8089'
	BROADCAST_FRONT_ADDRESS = '10.142.117.196'
	TSINGHUA_ADDR = 'http://115.182.62.174:8000'
	TURING_ADDR = 'http://doge.sogou-inc.com:1000/'
	TURING_BLOCK_WORD = '../../data/turing.block.word'
	TURING_APIKEY = '../../data/turing.apikey'
	XIAOBING_BLOCK_WORD = '../../data/xiaobing.block.word'
	REWRITE_ADDR = 'http://10.142.99.202:8880'
	WHITELIST_QQGROUP_ADDR = "http://quickanswer02.swc.zw.ted:5555" #???
	FAQ_ADDR = 'http://10.134.65.35:5555' # for boao
	'''
