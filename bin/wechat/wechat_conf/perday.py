#!/usr/bin/python
#coding=utf-8

#a1. import sys
import datetime
import re
import sys
sys.path.append('../lib')
#a2. import thirdparty
import requests
import urllib
#a3. import applicaiton
from config import redis_pool_perday as redis_pool 
import lxml.etree as etree
from perday_conf import PerdayConf
#b. env & global
time_p = re.compile('^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')
username_p = re.compile('<FromUserName><!\[CDATA\[(.*)\]\]></FromUserName>')
event_p = re.compile('<Event><!\[CDATA\[(.*)\]\]></Event>')
signature_p = re.compile('POST /weixin\?signature=(.*)&timestamp')


time = ''
username = ''
thing = 'message'

def read_one_day(date):

	reg_user = set()
	leav_user = set()
	message_user = set()
	num_msg = 0
	handle_map = {}


	try:
		f = open('/search/odin/wechat/trunk/logs/wechat-log-' + date.replace('-', ''))
	except:
		f = open('/search/odin/wechat/trunk/logs/wechat.log') # if no request, then no auto rename

	line = f.readline()
	while line:

		if line.find('server_time') == 0:
			line = f.readline()
			time = time_p.findall(line)[0]
			cur_date = time.split(' ')[0]
			if cur_date != date:
				line = f.readline()
				continue
				
			line = f.readline()
			line = f.readline()
			line = f.readline()
			line = f.readline()
			line = f.readline()

			assert line == 'request_xml:\n'

			request_xml = ''
			while line.find('</xml>') != 0:
				line = f.readline()
				request_xml += line

			while line.find('handle_type:') != 0:
				line = f.readline()
			line = f.readline()
			handle_type = line.strip()

			'''
			handle_type = ''
			'''

			#--------------finished parsing one--------------
				
			username = username_p.findall(request_xml)[0]
			if username in PerdayConf.inner_user_dict.keys():
				pass
			elif len(event_p.findall(request_xml)) > 0:
				event = event_p.findall(request_xml)[0]
				if event == 'subscribe':
					reg_user.add(username)
				elif event == 'unsubscribe':
					leav_user.add(username)
				elif event == 'LOCATION': # Upper Case 'LOCATION' means automatic reported location
					pass
				else: # other message
					num_msg += 1
					message_user.add(username)
					if not handle_map.has_key(handle_type):
						handle_map[handle_type] = 0
					handle_map[handle_type] += 1
			else:
				num_msg += 1
				message_user.add(username)
				if not handle_map.has_key(handle_type):
					handle_map[handle_type] = 0
				handle_map[handle_type] += 1

		line = f.readline()

	f.close()


	r = redis.Redis(connection_pool = redis_pool)
	r.set('num_reg:' + date, len(reg_user))
	r.set('num_leav:' + date, len(leav_user))
	r.set('num_incr:' + date, (len(reg_user) - len(leav_user)))

	previous_day_user_cnt = int(r.get('total_user:' + date_incr(date, -1)))
	r.set('total_user:' + date, previous_day_user_cnt + len(reg_user) - len(leav_user))

	r.set('num_msg:' + date, num_msg)
	r.set('num_msg_user:' + date, len(message_user))
	if len(message_user) == 0:
		r.set('avg_msg:' + date, 0)
	else:
		r.set('avg_msg:' + date, (float(num_msg) / len(message_user)))

	r.delete('reg_user:' + date)
	for item in reg_user:
		r.rpush('reg_user:' + date, item)

	r.delete('message_user:' + date)
	for item in message_user:
		r.rpush('message_user:' + date, item)

	r.delete('handle_type:' + date)
	r.hmset('handle_type:' + date, handle_map)

def date_incr(date, interval):
	d1 = datetime.datetime.strptime(date, '%Y-%m-%d')
	d2 = d1 + datetime.timedelta(interval)
	date2 = d2.strftime('%Y-%m-%d')
	return date2

def get_current_day_user(date):			
	r = redis.Redis(connection_pool = redis_pool)
	num_reg = r.get('num_reg:' + date)
	num_leav = r.get('num_leav:' + date)
	num_incr = r.get('num_incr:' + date)
	total_reg = r.get('total_user:' + date)
	return num_reg, num_leav, num_incr, total_reg

def get_current_day_msg(date):			
	r = redis.Redis(connection_pool = redis_pool)
	num_msg = r.get('num_msg:' + date)
	num_msg_user = r.get('num_msg_user:' + date)
	avg_msg = r.get('avg_msg:' + date)
	return num_msg, num_msg_user, avg_msg

def get_current_day_msg_detail(date):			
	r = redis.Redis(connection_pool = redis_pool)
	m = r.hgetall('handle_type:' + date)
	return m
	
	

def get_retention(date, interval):			
	d1 = datetime.datetime.strptime(date, '%Y-%m-%d')
	d2 = d1 + datetime.timedelta(interval)
	date2 = d2.strftime('%Y-%m-%d')
	
	r = redis.Redis(connection_pool = redis_pool)
	set2 = set(r.lrange('message_user:' + date2, 0, -1))
	set1 = set(r.lrange('reg_user:' + date, 0, -1))

	retention_num = len(set1 & set2)
	if len(set1) == 0:
		retention_rate = 0
	else:
		retention_rate = float(retention_num) / len(set1)

	return len(set1), retention_rate

def compose_email(date):
	uid = 'ps_id@sogou-inc.com'
	fr_name = '搜狗汪仔'.decode('utf8', 'ignore').encode('gbk', 'ignore')
	fr_addr = 'ps_id@sogou-inc.com'
	title = ('搜狗汪仔日报 - %s' % date).decode('utf8', 'ignore').encode('gbk', 'ignore')

	today_user_table = '''
<h3>用户统计</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="red" scope="col">新增人数</th>
            <th class="red" scope="col">取关人数</th>
            <th class="red" scope="col">净增人数</th>
            <th class="red" scope="col">累积人数</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>%d</td>
            <td>%d</td>
            <td>%d</td>
            <td>%d</td>
        </tr>
    </tbody>
</table>
''' % tuple(map(lambda x:int(x), list(get_current_day_user(date))))

	today_message_table = '''
<h3>消息统计</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="green" scope="col">消息总数</th>
            <th class="green" scope="col">发送人数</th>
            <th class="green" scope="col">人均消息</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>%d</td>
            <td>%d</td>
            <td>%.1f</td>
        </tr>
    </tbody>
</table>
''' % tuple(map(lambda x:float(x), list(get_current_day_msg(date))))


	m = get_current_day_msg_detail(date)
	#----------------------------------------------------------
	brief_msg_table = '''
<h3>消息详情统计-汇总</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="green" scope="col">类型</th>
            <th class="green" scope="col">占比</th>
        </tr>
    </thead>
    <tbody>
'''
	mm = {}
	for k in m:
		new_k = k.split('-')[0]
		if not mm.has_key(new_k):
			mm[new_k] = 0
		mm[new_k] += int(m[k])
	n = sorted(mm.items(), lambda x, y: cmp(int(x[1]), int(y[1])), reverse = True)	
	total_msg_num = 0
	for (k, v) in n:
		total_msg_num += int(v)
	for (k, v) in n:
		brief_msg_table += '<tr><td>%s</td><td>%.2f%%</td></tr>' % (k, 100 * float(v) / total_msg_num)
	brief_msg_table += '</tbody></table>'


	#----------------------------------------------------------
	detail_msg_table = '''
<h3>消息详情统计-详细</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="green" scope="col">类型</th>
            <th class="green" scope="col">占比</th>
        </tr>
    </thead>
    <tbody>
'''
	n = sorted(m.items(), lambda x, y: cmp(int(x[1]), int(y[1])), reverse = True)	
	total_msg_num = 0
	for (k, v) in n:
		total_msg_num += int(v)
	for (k, v) in n:
		detail_msg_table += '<tr><td>%s</td><td>%.2f%%</td></tr>' % (k, 100 * float(v) / total_msg_num)
	detail_msg_table += '</tbody></table>'


	retention_table_1day = '''
<h3>近期留存统计 - 次日</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="blue" scope="col">日期</th>
            <th class="blue" scope="col">当日注册</th>
            <th class="blue" scope="col">次日留存率</th>
        </tr>
    </thead>
    <tbody>
'''

	for i in range(1, 8):
		date2 = date_incr(date, -i)
		num_reg, rate = get_retention(date2, 1)
		retention_table_1day += '<tr><td>%s</td><td>%d</td><td>%.2f%%</td></tr>' % (date2, num_reg, rate * 100)

	retention_table_1day += '</tbody></table>'

	retention_table_7day = '''
<h3>近期留存统计 - 7日</h3>
<table id="rounded-corner">
    <thead>
        <tr>
            <th class="blue" scope="col">日期</th>
            <th class="blue" scope="col">当日注册</th>
            <th class="blue" scope="col">7日留存率</th>
        </tr>
    </thead>
    <tbody>
'''

	for i in range(7, 14):
		date2 = date_incr(date, -i)
		num_reg, rate = get_retention(date2, 7)
		retention_table_7day += '<tr><td>%s</td><td>%d</td><td>%.2f%%</td></tr>' % (date2, num_reg, rate * 100)

	retention_table_7day += '</tbody></table>'

	body = '<h1>搜狗汪仔日报 - %s</h1>%s<br>%s<br>%s<br>%s<br>%s<br>%s' % (date, today_user_table, today_message_table, brief_msg_table, detail_msg_table, retention_table_1day, retention_table_7day)
	html = '<html><head>' + PerdayConf.css + '</head><body>' + body + '</body></html>'

	html = html.decode('utf8', 'ignore').encode('gbk', 'ignore')
	send_to = 'zhaohaizhou@sogou-inc.com'

	url = 'http://mail.portal.sogou/portal/tools/send_mail.php?uid=%s&fr_name=%s&fr_addr=%s&title=%s&body=%s&mode=html&maillist=%s&attname=&attbody=' % (uid, urllib.quote(fr_name), fr_addr, urllib.quote(title), urllib.quote(html), send_to)

	requests.get(url)

if len(sys.argv) > 1:
	date = sys.argv[1]
else:
	today = datetime.datetime.now().strftime('%Y-%m-%d')
	date = date_incr(today, -1)

read_one_day(date)
compose_email(date)
