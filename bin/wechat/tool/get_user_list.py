#a1. import sys
import json
import os
import sys

#a2. import thirdparty
import requests

sys.path.append('../')
sys.path.append('../lib')

#a3. import application
from tool import get_access_token_v2

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
	except:
		print 'error for %s' % user_info['openid']
		return ''

if __name__ == '__main__':
	account = sys.argv[1]
	lst = get_user_lst(account)

	token = get_access_token_v2(account)
	cnt = 0

	out = open('users', 'w')
	for openid in lst:
		cnt += 1
		if cnt == 400:
			token = get_access_token_v2(account)
			cnt = 0
		record  = get_user_info(token, openid)
		if record:
			out.write(record + '\n')
	out.close()
