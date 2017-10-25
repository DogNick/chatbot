#coding=utf-8

from __future__ import division
import os
import re
import sys
import pdb
import json
import time
import random
import logging
import traceback
import itertools

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, '../common'))
sys.path.append(os.path.join(curr_dir, '../../lib'))
sys.path.append(os.path.join(curr_dir, '../'))

from trie import *
from common_method import *
from preprocessing import *
from tencent_segment import *

detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


curr_dir = os.path.dirname(os.path.abspath(__file__))
tsinghua_image_file = os.path.join(curr_dir, '../../data/tsinghua_qa/image_map.txt')
pattern_dir = os.path.join(curr_dir, '../../data/whitelist/whitelist.pattern')
answer_dir = []
answer_dir.append(os.path.join(curr_dir, '../../data/whitelist/whitelist.value'))
query_dir = []
query_dir.append(os.path.join(curr_dir, '../../data/whitelist/whitelist.post_response'))
pattern_cont_dir = os.path.join(curr_dir, '../../data/whitelist/whitelist.pattern_containment')


p_qus = re.compile('吗|么')
p_people = re.compile('(你表现|自己)')
p_weather = re.compile('(天气|空气质量)')
yzdd_pattern_tree = TagMake()
blacklist_tree = TagMake()
pattern_id = {}					#pattern到id的映射，一个pattern可能对应多个id（id是唯一的，一个id对应一组pattern）
id_pattern = {}					#id到pattern的映射，一个id对应多个pattern
id_answerid = {}				#id到answer_id的映射，可能出现多个id对应一个answer_id
whitelist_value = {}			#存放answer
whitelist_post_response = {}	#存放白名单query
pattern_containment = {}		#pattern包含关系，key和value都是id，每个key可以对应一个dict
TOPN = 3
last_answer_id = {}


sources = {
		'yzdd_onsite':'yzdd',
		'common_show':'common_show',
		'show_medical':'show_medical',
		'weimi':'weimi',
		'qqgroup':'qqgroup',
		'tsinghua_robot':'tsinghua_robot'
}

# 加载所有pattern
def load_pattern_text():
	global pattern_id
	global id_pattern
	global id_answerid
	try:
		inputs = open(pattern_dir, 'r')
		for line in inputs:
			line = line.strip()
			items = line.split('\t')
			if len(items) != 3:
				continue
			pattern_ids = items[0]
			pattern = items[1]
			answer_id = items[2]
			patterns = items[1].split(' ')
			id_answerid[pattern_ids] = answer_id
			j = 0
			while j < len(patterns):
				key = patterns[j]
				if key == '':
					j += 1
					continue
				yzdd_pattern_tree.add_tag(key)
				if pattern_ids not in id_pattern:
					id_pattern[pattern_ids] = dict()
				id_pattern[pattern_ids][key] = 0
				if key not in pattern_id:
					pattern_id[key] = dict()
				pattern_id[key][pattern_ids] = 0
				j += 1
		inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))


# 加载answer
def load_whitelist_value():
	global whitelist_value
	try:
		for path in answer_dir:
			inputs = open(path, 'r')
			for line in inputs:
				line = line.strip()
				items = line.split('\t')
				if len(items) != 2:
					continue
				whitelist_value[items[0]] = items[1]
			inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))


# whitelist_post_response: 加载白名单所有title
def load_whitelist_title():
	global whitelist_post_response
	try:
		for path in query_dir:
			inputs = open(path, 'r')
			for line in inputs:
				if line.find('#') == 0:
					continue
				line = line.strip()
				items = line.split('\t')
				if len(items) != 2:
					continue
				segs = seg_with_pos(items[0].decode('utf-8'))
				query_utf8 = get_norm_query(segs).encode('utf-8')
				whitelist_post_response[query_utf8] = items[1]
			inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))


# 判断pattern之间的相互包含关系
def load_pattern_containment():
	global pattern_containment
	try:
		inputs = open(pattern_cont_dir, 'r')
		for line in inputs:
			items = line.strip().split('\t')
			id1 = items[0].split(':')[0]
			id2 = items[1].split(':')[0]
			if id1 not in pattern_containment:
				pattern_containment[id1] = dict()
			pattern_containment[id1][id2] = 0
		inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))


def init_image_map():
	'''
		功能: 加载清华入学小助手图片信息
		return:
			image_map: 清华入学小助手图片映射信息
	'''
	image_map = {}
	try:
		inputs = open(tsinghua_image_file, 'r')
		for line in inputs:
			items = line.strip().split('\t')
			if len(items) != 2:
				continue
			image_map[items[0]] = items[1]
		inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
	return image_map


# init初始化
begin_time = time.time()
load_pattern_text()
load_whitelist_value()
load_whitelist_title()
load_pattern_containment()
image_map = init_image_map()
cost = str(round(time.time()-begin_time, 3)*1000)
detlog.info('[intervene_init] [whitelist] [cost=%sms]' % (cost))


# 判断用户上一次的意图是否的技能
def is_user_last_intent_is_skill(acc_params):
	flag = False
	if 'context' in acc_params:
		if 'last_from' in acc_params['context'] and 'last_time' in acc_params['context']:
			if acc_params['context']['last_from'] == "special_skill" and time.time()-acc_params['context']['last_time'] <= 600:
				detlog.info('[intervene_INFO] [whitelist] query in session 1')
				flag = True
		if flag == False and 'in_session' in acc_params['context'] and acc_params['context']['in_session'] == 'group_special_skill':
			detlog.info('[intervene_INFO] [whitelist] query in session 2')
			flag = True
	return flag


# 全角转半角
def strQ2B(ustring):
	rstring = ''
	for uchar in ustring:
		inside_code = ord(uchar)
		if inside_code == 12288:
			inside_code = 32
		elif (inside_code >= 65281 and inside_code <= 65374):
			inside_code -= 65248
		rstring += unichr(inside_code)
	return rstring


# 输出所有的匹配情况
def print_all(answer_list, flag=1):
	for line_id in answer_list:
		flags = True
		tmp = '>>>>>>>>>' + str(line_id) + '\t'
		for pat in answer_list[line_id]:
			tmp += pat + ':' + str(answer_list[line_id][pat]) + '\t'
			#if flag == 1 and answer_list[line_id][pat] == 0:
			#	flags = False
			#	break
		if flags == True:
			print tmp


# 给定id得到完整pattern
def id_pattern_line(ids):
	tmp = ''
	for key in id_pattern[ids]:
		tmp += key + ' '
	tmp = tmp[:-1]
	return tmp


# pattern匹配过程
def pattern_match(query_utf8, result, end_flag, source, acc_params):
	log_str = '[intervene_INFO] [whitelist] [query=%s]' % (query_utf8)
	try:
		answer_list = {}
		final_id = None
		final_answer_id = None
		id_list = []
		max_pattern = 0
		max_length = 0
		patterns = ''
		for pattern_s in result:
			pattern = pattern_s[0]
			patterns += pattern + ' '
			for line_id in pattern_id[pattern]:
				if line_id not in answer_list:
					answer_list[line_id] = id_pattern[line_id].copy()
				answer_list[line_id][pattern] = 1
		log_str += ' [pattern=%s]' % patterns[:-1]
		if len(answer_list) == 0:
			detlog.info(log_str)
			return final_answer_id, id_list
		complete_id = ''
		final_id_list = ''
		id_list_tmp = {}
		for line_id in answer_list:
			flag = True
			people_flag = False
			length = 0
			for pattern in answer_list[line_id]:
				length += len(pattern)
				if answer_list[line_id][pattern] == 0:
					if pattern == 'WHO':
						if p_people.search(query_utf8) == None and p_weather.search(query_utf8) == None:
							answer_list[line_id][pattern] = 1
							people_flag = True
						else:
							flag = False
							break
					elif pattern == 'QUS$':
						if p_qus.search(query_utf8) != None:
							answer_list[line_id][pattern] = 1
						else:
							flag = False
							break
					elif pattern == '':
						answer_list[line_id][pattern] = 1
					else:
						flag = False
						break
			if flag == True:
				source_id = get_answer_id(source, id_answerid[line_id], acc_params.get('robot_model', '1'))
				if source_id == '':
					continue
				if float(length/len(query_utf8)) < 0.5:
					continue
				complete_id += str(line_id) + '(' + id_pattern_line(line_id) + ':' + source_id + ') '
				id_list_tmp[line_id] = (len(answer_list[line_id]), length, people_flag)
		for ids in id_list_tmp:
			if ids in pattern_containment:
				if end_flag != 1:
					continue
				else:
					is_delete_flag = False
					for key in pattern_containment[ids]:
						if key in id_list_tmp:
							is_delete_flag = True
							break
					if is_delete_flag:
						continue
			source_id = get_answer_id(source, id_answerid[ids], acc_params.get('robot_model', '1'))
			final_id_list += str(ids) + '(' + id_pattern_line(ids) + ':' + source_id + ') '
			id_list.append(source_id)
			if id_list_tmp[ids][2] == True and final_id != '' and final_id != None:
				continue
			if final_id == None or id_list_tmp[ids][0] > max_pattern or (id_list_tmp[ids][0] == max_pattern and id_list_tmp[ids][1] > max_length):
				final_id = ids
				max_pattern = id_list_tmp[ids][0]
				max_length = id_list_tmp[ids][1]
		#print_all(answer_list)
		log_str += ' [match_id_list=%s]' % complete_id[:-1]
		log_str += ' [final_id_list=%s]' % final_id_list[:-1]
		if final_id != None:
			log_str += ' [final_id=%s]' % str(final_id)
		if final_id != None and final_id in id_answerid:
			final_answer_id = get_answer_id(source, id_answerid[final_id], acc_params.get('robot_model', '1'))
			log_str += ' [answer_id=%s]' % final_answer_id
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
	detlog.info(log_str)
	return final_answer_id, id_list


# 随机打乱列表,取TOPN个回答
def get_yzdd_result(items, debug_info, source):
	default_ret = []
	temp = []
	for item in items:
		if item == '':
			continue
		answer = get_answer(item, source, debug_info)
		temp.append(answer)
	random.shuffle(temp)
	i = 0
	for item in temp:
		i += 1
		if i > TOPN:
			break
		default_ret.append((item, debug_info))
	return default_ret


def get_answer_id(source, text, robot_model):
	answer_id = ''
	normal_id = ''
	items = text.split('|')
	if robot_model != '1' and (source.find('yzdd') != -1 or source == 'common_show' or source == 'show_medical'):
		for item in items:
			if item.find('robot' + robot_model) != -1:
				answer_id = item
				break
			elif item.find(source) != -1:
				answer_id = item
				break
			elif item.find('normal') != -1 and source != 'weimi':
				normal_id = item
	else:
		for item in items:
			if item.find(source) != -1:
				answer_id = item
				break
			elif item.find('normal') != -1 and source != 'weimi':
				normal_id = item
	if answer_id == '' and normal_id != '':
		answer_id = normal_id
	return answer_id


#非yzdd_onsite来源的answer去掉action
def get_answer(text, source, debug_info):
	action = []
	if text.find('{action:') != -1:
		while True:
			pos1 = text.find('{action:')
			pos2 = text.find('}', pos1)
			if pos1 != -1 and pos2 != -1:
				act = text[pos1+8:pos2]
				text = text[0:pos1] + text[pos2+1:]
				action.append({'id':act, 'position':0})
			else:
				break
	if action != []:
		debug_info['action'] = action
	return text, debug_info


def get_random_answer(answer_id, source, debug_info):
	answer = ''
	if answer_id not in whitelist_value:
		return answer
	text = whitelist_value[answer_id].decode('utf-8')
	text = strQ2B(text)
	items = text.split('<br>')
	#if source == 'yzdd':
	#	default_ret = get_yzdd_result(items, debug_info, source)
	#else:
	index = random.randint(0, len(items)-2)		#减2是因为最后多一个<br>,会有空串
	if answer_id in last_answer_id:
		while index == last_answer_id[answer_id]:
			index = random.randint(0, len(items)-2)
	if len(items) > 2:
		last_answer_id[answer_id] = index
	answer, debug_info = get_answer(items[index], source, debug_info)
	return answer, debug_info


def get_tsinghua_answer(answer, debug_info):
	if answer.find('<command>') != -1:
		content = answer
		answer = get_between(content, '', '<command>')
		command = get_between(content, '<command>', '</command>')
		if command != '':
			debug_info['card'] = {}
			debug_info['card']['tmpl'] = get_between(command, '<tmpl>', '</tmpl>')
			debug_info['card']['data'] = []
			_, results = get_between_all(command, '<data>', '</data>')
			for each in results:
				title = get_between(each, '<title>', '</title>')
				image = get_between(each, '<image>', '</image>')
				content = get_between(each, '<content>', '</content>').replace('<brbr>', '\n')
				if image in image_map:
					image = image_map[image].replace('http', 'https')
				if content.find('|') != -1:
					items = content.split('|')
					for item in items:
						detail = {}
						detail['title'] = title
						detail['image'] = image
						detail['content'] = item
						debug_info['card']['data'].append(detail)
				else:
					detail = {}
					detail['title'] = title
					detail['image'] = image
					detail['content'] = content
					debug_info['card']['data'].append(detail)
	return answer, debug_info


def query_match_final(query_utf8, source, acc_params, debug_info):
	flag = True
	default_ret = []
	new_query_utf8 = ''
	answer_id_list = whitelist_post_response[query_utf8]
	answer_id = get_answer_id(source, answer_id_list, acc_params.get('robot_model', '1'))
	if answer_id == '':
		answer = None
		debug_info['err'] = 'not match'
		flag = False
	else:
		answer, debug_info = get_random_answer(answer_id, source, debug_info)
		answer = answer.replace('<brbr>', '\n')
		if answer_id.find('tsinghua_robot') != -1:
			answer, debug_info = get_tsinghua_answer(answer, debug_info)
		debug_info['from'] = 'precision_chat'
		debug_info['flag'] = 'title'
		debug_info['answer_id'] = answer_id
		debug_info['sub_type'] = '白名单-精准'
		log_str = '[intervene_INFO] [whitelist] [query=%s] [answer_id=%s] match perfectly' % (query_utf8, answer_id)
		detlog.info(log_str)
	if answer == '':
		answer = None
	default_ret.append((answer, debug_info))
	return flag, default_ret


def pattern_match_final(query_utf8, source, debug_info, end_flag, acc_params):
	answer = None
	result = []
	default_ret = []
	result = yzdd_pattern_tree.make_all(query_utf8)
	if len(result) == 0:
		debug_info['err'] = 'not match'
		default_ret = [(answer, debug_info)]
		log_str = '[intervene_INFO] [whitelist] [query=%s] not match' % (query_utf8)
		detlog.info(log_str)
	else:
		dic = {}
		final_id, id_list = pattern_match(query_utf8, result, end_flag, source, acc_params)
		#print final_id
		if len(id_list) == 0:
			debug_info['err'] = 'not match'
			default_ret = [(answer, debug_info)]
			return default_ret
		if final_id != None:
			dic[final_id] = 0
			answer, debug_info = get_random_answer(final_id, source, debug_info)
			answer = answer.replace('<brbr>', '\n')
			if final_id.find('tsinghua_robot') != -1:
				answer, debug_info = get_tsinghua_answer(answer, debug_info)
			debug_info['flag'] = 'pattern'
			debug_info['answer_id'] = final_id
			debug_info['sub_type'] = '白名单-pattern'
			default_ret.append((answer, debug_info))
		for match_id in id_list:
			if match_id in dic:
				continue
			else:
				dic[match_id] = 0
			if match_id == final_id:
				continue
			answer, debug_info = get_random_answer(match_id, source, debug_info)
			answer = answer.replace('<brbr>', '\n')
			if match_id.find('tsinghua_robot') != -1:
				answer, debug_info = get_tsinghua_answer(answer, debug_info)
			debug_info['flag'] = 'pattern'
			debug_info['answer_id'] = match_id
			debug_info['sub_type'] = '白名单-pattern'
			default_ret.append((answer, debug_info))
	return default_ret


# query匹配过程
def select_answer(query_utf8, source, acc_params):
	default_ret = []
	debug_info = {'from':'whitelist_pattern'}
	query_flag = False
	end_flag = acc_params['end_flag']
	if end_flag:			#与白名单完全匹配
		if query_utf8 in whitelist_post_response:
			query_flag, default_ret = query_match_final(query_utf8, source, acc_params, debug_info)
		else:
			new_query_utf8 = get_norm_query(acc_params['seg']).encode('utf-8')
			if new_query_utf8 in whitelist_post_response:
				query_flag, default_ret = query_match_final(new_query_utf8, source, acc_params, debug_info)
	if query_flag == False:		#pattern系统
		default_ret = pattern_match_final(query_utf8, source, debug_info, end_flag, acc_params)
	return default_ret


def get_source_format(source):
	if source in sources:
		source = sources[source]
	else:
		source = 'normal'
	return source


def need_req(query, source='', acc_params={}):
	debug_info = {'from':'whitelist_pattern'}
	default_ret = []
	try:
		if source == 'qcloud':
			return False, [(None, debug_info)]
		if query.find(u'是你爸') != -1 or query.find(u'是你妈') != -1 or query.find(u'是你爹') != -1 or query.find(u'是你娘') != -1:
			answer = u'请不要套路本汪'
			debug_info = {'from':'whitelist_pattern', 'status':'bad question'}
			return False, [(answer, debug_info)]
		source = get_source_format(source)
		default_ret = select_answer(query.encode('utf-8'), source, acc_params)
		if default_ret[0][0] != None and is_user_last_intent_is_skill(acc_params):
			debug_info = default_ret[0][1]
			debug_info['status'] = 'last intention is special skill'
			default_ret = [(None, debug_info)]
	except Exception, e:
		exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
		default_ret = [(None, debug_info)]
	return False, default_ret


# 本地测试接口
def get_whitelist_pattern(query, source='', acc_params={}):
	flag, default_ret = need_req(query, source, acc_params)
	return default_ret


if __name__ == '__main__':
	# 配置logging
	detlog.setLevel(logging.INFO)
	exclog.setLevel(logging.INFO)
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


	source = 'show_medical'
	querys = [u'你现在在哪', u'介绍一下你自己吧', u'想跟我们的选手比赛吗', u'你觉得我们的选手怎么样']
	querys = [u'你觉得王小川怎么样', u'想跟王小川比赛吗', u'你觉得你自己表现的怎么样', u'知道我吗']
	querys = [u'你会说中文吗', u'怎么评价王小川的表现', u'王小川表现如何']
	querys = [u'你会说中文吗', u'你好', u'你有什么特异功能']
	querys = [u'你觉得王小川表现的怎么样']
	querys = [u'今天感觉怎么样']
	querys = [u'你觉得这个节目怎么样']
	querys = [u'你是挺帅的嗯我想问你一个问题,你觉得是你更加厉害,还是百度的小度更强大']
	querys = [u'汪仔，你爸爸是谁', u'汪仔，你是哪个星座']
	querys = [u'你爸爸是谁']
	querys = [u'汪仔你喜欢吃什么呀？']
	querys = [u'好遗憾啊汪仔，你有什么感想']
	querys = [u'你爸爸是谁啊', u'你是谁啊']
	querys = [u'你好', u'你是谁啊', u'唱歌', u'唱歌啊', u'呵呵', u'牛逼']
	querys = [u'你怎么看习大大', u'北京3月20日尾号3限行吗']
	querys = [u'你会干什么呀']
	querys = [u'你老婆跑了', u'不饿', u'你多大了']
	querys = [u'你好', u'你名字叫什么啊']
	#for query in querys:
	while True:
		print '>>>>>>>>>>>>>>>>>>'
		query = raw_input('query:')
		b = time.time()
		query = get_query_correction(query.decode('utf-8'), source)
		acc_params = preprocessing(query, source)
		acc_params['robot_model'] = '2'
		#acc_params['context'] = dict()
		#acc_params['context']['last_from'] = 'special_skill'
		#acc_params['context']['last_time'] = 1499040020.578549
		print json.dumps(acc_params, ensure_ascii=False)
		default_ret = get_whitelist_pattern(query, source, acc_params)
		e = time.time()
		print 'query:' + query.encode('utf-8')
		for ret in default_ret:
			answer = ret[0]
			debug_info = ret[1]
			if answer == None:
				answer = ''
			print 'answer:' + answer.encode('utf-8')
			print 'debug:' + json.dumps(debug_info, ensure_ascii=False)
		print 'cost:' + str(round((e-b)*1000, 2)) + 'ms'
		print '\n\n'

