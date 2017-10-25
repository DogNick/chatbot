#coding=utf-8

"""
	数据来源主要分为两部分：立知和图谱
"""

import common_method as comm


# 目前lizhi类型。key:pvtype  value:(vrid, priority_id, 名称)
LIZHI_ID = {
		'15_300_1':('50022101', 'lizhi', u'all-短答案'),	#如果只有支持文本, priority_id=lizhi_support
		'15_300_2':('50022201', 'lizhi', u'长答案-百科类'),
		'15_300_3':('50022301', 'lizhi_support', u'长答案-通用'),
		'15_300_4':('50022401', 'lizhi', u'长答案-定义类'),
		'15_300_5':('50022501', 'lizhi_support', u'列表-通用'),
		'15_300_6':('50022601', 'lizhi_census', u'all-观点互斥'),
		'15_300_7':('50023601', 'lizhi', u'短答案-无支持文本'),
		'15_300_8':('50024201', 'lizhi_support', u'列表-多图经验'),
		'15_300_9':('50024301', 'lizhi_support', u'列表-无图单图经验'),
		'15_300_10':('50024401', 'lizhi', u'长答案-权威站点'),
		'15_300_11':('50024501', 'lizhi_ugc', u'长答案-ugc站点'),
}


def parse_lizhi_answer(data, query, answer, debug_info):
	"""解析立知xml数据
	Args:
		data: 每条数据的xml数据，编码Unicode
		query: query，编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raise:
	"""
	data = data[data.rfind('<doc>'):]
	debug_info['sub_type_id'] = 'lizhi'
	debug_info['priority_id'] = 'lizhi'
	debug_info['title'] = comm.get_between(data, '<title><![CDATA[', ']]></title>')
	debug_info['url'] = comm.get_between(data, '<url><![CDATA[', ']]></url>')
	debug_info['pvtype'] = comm.get_between(data, 'pvtype="', '" vrid="')
	debug_info['vrid'] = comm.get_between(data, 'vrid="', '"')
	debug_info['display_type'] = comm.get_between(data, '<display type="', '">')
	if debug_info['pvtype'] in LIZHI_ID:
		answer, debug_info = parse_lizhi_precise(data, answer, debug_info)
	else:
		answer, debug_info = parse_lizhi_tupu(data, query, answer, debug_info)
	return answer, debug_info

def parse_lizhi_precise(data, answer, debug_info):
	"""解析精准问答xml数据
	Args:
		data: 每条数据的xml数据，编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raise:
	"""
	debug_info['priority_id'] = debug_info['sub_type_id'] = LIZHI_ID[debug_info['pvtype']][1]
	debug_info['details'] = LIZHI_ID[debug_info['pvtype']][2]
	if debug_info['pvtype'] == '15_300_1' or debug_info['pvtype'] == '15_300_7':
		answer, debug_info = parse_precise_lizhi_short_qa(data, answer, debug_info)
	elif debug_info['pvtype'] == '15_300_5' or debug_info['pvtype'] == '15_300_8' or debug_info['pvtype'] == '15_300_9':
		answer, debug_info = parse_precise_lizhi_list(data, answer, debug_info)
	else:
		answer = comm.get_between(data, '<answer><![CDATA[', ']]></answer>')
	return answer, debug_info

def parse_precise_lizhi_short_qa(data, answer, debug_info):
	"""解析短答案
	Args:
		data: 每条数据的xml数据，编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raise:
	"""
	answer = comm.get_between(data, '<short_answer><![CDATA[', ']]></short_answer>')
	if answer == '' or answer == None:
		if debug_info['pvtype'] == '15_300_1':
			debug_info['priority_id'] = debug_info['sub_type_id'] = 'lizhi_support'
		answer = comm.get_between(data, '<answer><![CDATA[', ']]></answer>')
	return answer, debug_info

def parse_precise_lizhi_list(data, answer, debug_info):
	"""解析列表类
	Args:
		data: 每条数据的xml数据，编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raise:
	"""
	flag, items = comm.get_between_all(data, '<answer>', '</answer>')
	for (index, item) in enumerate(items):
		if index == 0:
			answer = item
		else:
			answer += '\n' + item
	return answer, debug_info

def parse_lizhi_tupu(data, query, answer, debug_info):
	"""解析图谱
	Args:
		data: 每条数据的xml数据，编码Unicode
		query: 编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raise:
	"""
	if data.find('<voiceinfo>') != -1 and data.find('<viewchoicelist>') == -1:
		answer = comm.get_between(data, '<voiceinfo>', '</voiceinfo>')
		debug_info['details'] = 'answer from tupu voiceinfo'
		if debug_info['vrid'] == '50005901':
			answer = answer[len(query):]
	if (answer == None or answer == '') and debug_info['display_type'] == '1':
		flag, items = comm.get_between_all(data, '<name link', '</name>')
		for item in items:
			answer += comm.get_between(item, '">', '') + ' '
	if (answer == None or answer == '') and debug_info['display_type'] == '3':			#核桃的功效
		flag, answer_list = comm.get_between_all(data, '<li t="', '" link')
		answer = ' '.join(answer_list)
	if (answer == None or answer == '') and debug_info['display_type'] == '4':			#西瓜的热量
		answer = comm.get_between(data, '<attribute name="', '"') + '是'
		tmp1 = comm.get_between(data, '<h4 t="', '"') + comm.get_between(data, 'note="', '"')
		if tmp1 != '':
			answer += tmp1
		else:
			flag, items = comm.get_between_all(data, '<name link', '</name>')
			if flag:
				for item in items:
					answer += comm.get_between(item, '">', '') + '; '
			else:
				answer = None
	if (answer == None or answer == '') and (debug_info['display_type'] == '5' or debug_info['display_type'] == '6' or debug_info['display_type'] == '7'):
		flag, items = comm.get_between_all(data, '<name link', '</name>')
		for item in items:
			answer += comm.get_between(item, '">', '') + '; '
	if (answer == None or answer == '') and data.find('<answerinfo>') != -1:
		answer = comm.get_between(data, '<answer><![CDATA[', ']]></answer>')
		debug_info['details'] = 'answer from tupu answerinfo'
	return answer, debug_info

