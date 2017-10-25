# coding=utf8

#a1. import sys
from datetime import datetime
import logging
import json
import os
import sys
import time
import traceback

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, '.'))
sys.path.append(os.path.join(curr_dir, '../'))
sys.path.append(os.path.join(curr_dir, '../../lib'))

#a2. import thirdparty
import redis
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#a3. import application
from tool import get_access_token_v2
from wechat_conf import Config, redis_pool_user_info, redis_pool_user_cmd


#b. env & global
detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")


def get_user_cmd(uid):
	try:
		r = redis.Redis(connection_pool = redis_pool_user_cmd)
		result = r.get('weixin_debug' + uid)
	except Exception, e:
		result = None
		exclog.error('\n%s' % (traceback.format_exc(e)))
	if result is None:
		result = 'debugoff'
	return result

def put_user_cmd(uid, debug):
	try:
		r = redis.Redis(connection_pool = redis_pool_user_cmd)
		r.set('weixin_debug' + uid, debug)
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
	return

def get_user_count(account):
	token = get_access_token_v2(account)
	url = 'https://api.weixin.qq.com/cgi-bin/user/get?access_token=%s&next_openid=%s' % (token, '')
	r = requests.get(url, verify = False)
	total = json.loads(r.text)['total']
	return total


def get_user_lst(account):
	token = get_access_token_v2(account)
	url = 'https://api.weixin.qq.com/cgi-bin/user/get?access_token=%s&next_openid=%s' % (token, '')
	r = requests.get(url, verify = False)
	lst = json.loads(r.text)['data']['openid']
	return lst


def get_user_info(token, openid):
	url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token=%s&openid=%s&lang=zh_CN' % (token, openid)
	r = requests.get(url, verify = False)
	user_info = json.loads(r.text)
	try:
		record = '%s\t%s\t%s\t%s\t%s\t%s\t%s' % (user_info['openid'], user_info['nickname'], user_info['sex'], user_info['language'], user_info['city'], user_info['province'], user_info['country'])
		record = record.encode('utf8')
		return record
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
		return ''


def progress_bar(count, width):
	sys.stdout.write('*' * (count % width))
	sys.stdout.flush()
	sys.stdout.write('\r')
	if count % width == 0:
		sys.stdout.write(' ' * width + '\r')
		sys.stdout.flush()

def init_redis_user_info(account):
	try:
		lst = get_user_lst(account)
		user_info_field = ['openid', 'nickname', 'sex', 'language', 'city', 'province', 'country', 'update_time']
		token = get_access_token_v2(account)
		detlog.info("the length of the lst : %d" % len(lst))
		cnt = 0
		for openid in lst:
			cnt += 1
			progress_bar(cnt, 50)
			if cnt == 800:
				token = get_access_token_v2(account)
				cnt = 0
			update_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
			user_info_lst = get_user_info(token, openid).split('\t')
			user_info_lst.append(update_time)
			user_info_dict = dict(zip(user_info_field, user_info_lst))

			update_user_all_info(openid, user_info_dict)
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
		return ''


def update_user_location(openid, lat, lng, glovar):
	token = get_access_token_v2(glovar.account)

	update_user_info(openid, 'Latitude', lat)
	update_user_info(openid, 'Longitude', lng)
	update_user_info(openid, 'update_time', time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()))


def add_user_info(openid, glovar):
	token = get_access_token_v2(glovar.account)
	user_info_field = ['openid', 'nickname', 'sex', 'language', 'city', 'province', 'country', 'update_time']
	user_info_lst = get_user_info(token, openid).split('\t')

	update_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
	user_info_lst.append(update_time)
	user_info_dict = dict(zip(user_info_field, user_info_lst))

	return update_user_all_info(openid, user_info_dict)


def update_user_all_info(openid, attr_dict):
	try:
		rc = redis.Redis(connection_pool = redis_pool_user_info)

		return rc.hmset(openid, attr_dict)
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
		return ''


def update_user_info(openid, key, value):
	try:
		rc = redis.Redis(connection_pool = redis_pool_user_info)

		return rc.hset(openid, key, value)
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
		return ''


def get_user_all_info(openid):
	try:
		rc = redis.Redis(connection_pool = redis_pool_user_info)

		return rc.hgetall(openid)
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
		return None


if __name__ == '__main__':
	account = sys.argv[1]
	init_redis_user_info(account)

