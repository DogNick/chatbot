#coding=utf-8

"""
	先判断是否有精准VR的数据，再判断是否有voiceinfo，最后根据vr的class_id解析对应的xml
"""

import common_method as comm


VR_CLASS_ID = {
		'70090207':('vr_weather', 'VR'),			#天气(国内)
		'70090212':('vr_weather', 'VR'),			#天气(国内)
		'70089406':('vr_weather', 'VR'),			#天气(国际)
		'70089409':('vr_weather', 'VR'),			#天气(国际)
		'20114101':('vr_air', 'VR'),				#空气质量
		'70087304':('vr_car_limit', 'VR'),			#汽车尾号限行
		'70087305':('vr_car_limit', 'VR'),			#汽车尾号限行
		'70087301':('vr_car_limit', 'VR'),			#汽车尾号限行
		'70087303':('vr_car_limit', 'VR'),			#汽车尾号限行
		'21210301':('vr_food', 'VR'),				#food
		'11008001':('vr_meiju', 'VR'),				#问问枚举
		'21376401':('vr_shiliao', 'VR'),			#健康食疗-宜吃
		'21377401':('vr_shiliao', 'VR'),			#健康食疗-忌吃
		'10000801':('vr_map', 'VR_map_1'),			#地图
		'21337801':('vr_leader', 'VR'),				#各国领导人
		'21406001':('vr_teshou', 'VR'),				#特首
		'70015901':('vr_menu', 'VR_url'),			#菜谱
		'70054404':('vr_car', 'VR'),				#汽车
		'70032612':('vr_xiehouyu', 'VR'),			#歇后语
		'70095802':('vr_xyxk', 'VR'),				#食物相克
		'70030301':('vr_kefu', 'VR'),				#客服
		'70030302':('vr_kefu', 'VR'),				#客服
		'20009908':('vr_kefu', 'VR'),				#客服
		'21193401':('vr_zgjm', 'VR'),				#周公解梦
		'21199001':('vr_exam', 'VR'),				#考试
		'20003643':('vr_exam', 'VR'),				#考试
		'21391901':('vr_baoxian', 'VR'),			#五险一金
		'21342701':('vr_olympic', 'VR'),			#奥运会
		'70094706':('vr_chengyu', 'VR'),			#成语
		'70094705':('vr_chengyu', 'VR'),			#成语(old)
		'70116905':('vr_chengyu', 'VR'),			#成语
		'70116906':('vr_chengyu', 'VR'),			#成语
		'70115308':('vr_chengyu2', 'VR_afanti'),	#词语成语(阿凡题)
		'70115309':('vr_chengyu2', 'VR_afanti'),	#词语成语(阿凡题), 用于糖猫
		'70115314':('vr_chengyu3', 'VR_afanti'),	#词语成语(阿凡题)
		'70115312':('vr_chengyu3', 'VR_afanti'),	#词语成语(阿凡题)
		'70112601':('vr_poem_author', 'VR'),		#诗人
		'70110926':('vr_poem_author', 'VR'),		#诗人
		'70110930':('vr_poem', 'VR'),				#诗词
		'70110936':('vr_poem_all', 'VR'),			#描写某类事物的诗句
		'21379001':('vr_jieri', 'VR'),				#节日
		'21411001':('vr_gaofeng', 'VR'),			#世界高峰
}


def parse_vr_answer(data, query, answer, debug_info):
	'''解析VR的xml数据
	Args:
		data: 每条数据的xml数据，编码Unicode
		query: query，编码Unicode
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Returns:
		answer: 编码Unicode
		debug_info: 每条数据的debug信息
	Raises:
	'''
	debug_info['query'] = query
	debug_info['sub_type_id'] = 'VR'
	debug_info['priority_id'] = 'VR'
	debug_info['url'] = comm.get_between(data, u'<url><![CDATA[', u']]></url>')
	debug_info['vr_class_id'] = comm.get_between(data, u'<classid>', u'</classid>')
	debug_info['vr_class_tag'] = comm.get_between(data, u'<classtag>', u'</classtag>')
	if data.find(u'<title><![CDATA[') != -1:
		debug_info['title'] = comm.get_between(data, u'<title><![CDATA[', u']]></title>')
	else:
		debug_info['title'] = comm.get_between(data, u'<title>', u'</title>')
	if (answer == None or answer == '') and data.find(u'<key><![CDATA[精准VR]]></key>') != -1:
		answer, debug_info = parse_vr_type_precise_vr(data, query, answer, debug_info)
	if (answer == None or answer == '') and data.find(u'<voiceinfo') != -1:
		answer, debug_info = parse_vr_type_voiceinfo(data, query, answer, debug_info)
	if answer == None or answer == '':
		if debug_info['vr_class_id'] in VR_CLASS_ID:
			debug_info['priority_id'] = VR_CLASS_ID[debug_info['vr_class_id']][1]
			vr_func = getattr(parse_vr, 'parse_' + VR_CLASS_ID[debug_info['vr_class_id']][0])
			answer, debug_info = vr_func(data, answer, debug_info)
	if debug_info['index'] >= 5:
		debug_info['priority_id'] = u'VR_rank'
	return answer, debug_info

def parse_vr_type_precise_vr(data, query, answer, debug_info):
	'''解析vr精准VR类型
	Args:
		data: 每条数据的xml数据，编码Unicode
		query: query，编码Unicode
		answer: 编码Unicode
		debug_info: debug_info信息
	Returns:
		answer: 编码Unicode
		debug_info: debug_info信息
	Raises:
	'''
	content = comm.get_between(data, u'<accurContent><![CDATA[', u']]></accurContent>')
	items = content.split(u'@|@')
	if items[0].find(u'&#&') != -1:
		answer = items[0].replace(u'&#&', u' ')
	elif items[1].find(u'http') == 0:
		answer = items[0] + u'的' + items[2] + u'：' + items[3]
	elif items[2] == '':
		answer = items[0] + u'的' + items[1] + u'：无'
	else:
		answer = items[0] + u'的' + items[1] + u'：' + items[2]
	debug_info['details'] = u'answer from 精准VR'
	return answer, debug_info

def parse_vr_type_voiceinfo(data, query, answer, debug_info):
	'''解析vr带有voiceinfo的类型
	Args:
		data: 每条数据的xml数据，编码Unicode
		query: 编码Unicode
		answer: 编码Unicode
		debug_info: debug_info信息
	Returns:
		answer: 编码Unicode
		debug_info: debug_info信息
	Raises:
	'''
	voiceinfo = comm.get_between(data, u'<voiceinfo', u'</voiceinfo>')
	answer = comm.get_between(voiceinfo, u'<![CDATA[', u']]>')
	debug_info['details'] = u'answer from vr voiceinfo'
	if answer.find('{') != -1:
		debug_info['orig'] = answer
		debug_info['details'] += u', need other resources'
		answer = None
	if answer == None or answer == '':
		if debug_info['vr_class_id'] == '21343201':
			qoinfo = comm.get_between(data, u'<qoinfo', '\n')
			if qoinfo.find(u'vrQuery="万年历"') != -1:
				content = comm.get_between(qoinfo, u'vrData="', u'"')
				nongli = content[content.rfind(u' ')+1:]
				items = nongli.split(u'-')
				if len(items) == 3:
					answer = u'是农历' + items[0] + u'年' + items[1] + u'月'
					if len(items[2]) == 1:
						answer += u'初' + items[2]
					else:
						answer += items[2]
					debug_info['details'] = u'answer from qoinfo'
	if answer != None and answer.find(u'为您找到') != -1:
		debug_info['orig'] = answer
		debug_info['details'] += u', bad answer'
		answer = None
	return answer, debug_info


class ParseVR():
	def parse_vr_weather(self, data, answer, debug_info):
		'''解析vr天气
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		data = comm.get_between(data, u'<div class="more-day-box">', u'<div class="moreLink">')
		flag, items = comm.get_between_all(data, u'<a href=', u'</a>')
		if flag:
			for (index, item) in enumerate(items):
				if index == 0:		#昨日天气
					continue
				if answer == '' or answer == None:
					answer = ''
				else:
					answer += u';'
				tmp = comm.get_between(item, u'">', u'<i>')
				answer += comm.get_between(tmp, u'">', u'')
				answer += u'(' + comm.get_between(item, u'<i>', u'</i></p>') + u')'
				answer += comm.get_between(item, u'<p class="temperature">', u'</p>')
				tmp = comm.get_between(item, u'<p class="desp"', u'</p>')
				answer += u',' + comm.get_between(tmp, u'">', u'')
				answer += u',' + comm.get_between_last(item, u'<p>', u'</p>')
		return answer, debug_info

	def parse_vr_air(self, data, answer, debug_info):
		'''解析vr空气质量
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if data.find(u'<div class="num">') != -1:
			answer = comm.get_between(data, u'<div class="num">', u'</div>')
		if data.find(u'<div class="detail-info"><div class="state lv') != -1:
			tmp = comm.get_between(data, u'<div class="detail-info">', u'</div>')
			answer += u',' + comm.get_between(tmp, u'">', u'')
		if data.find(u'<div class="txt">') != -1:
			answer += u',' + comm.get_between(data, u'<div class="txt">', u'</div>')
		return answer, debug_info

	def parse_vr_car_limit(self, data, answer, debug_info):
		'''解析vr汽车限行
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = ''
		flag1, dates = comm.get_between_all(data, u'<th scope="col">', u'</th>')
		flag2, xianxing = comm.get_between_all(data, u'<td>', u'</td>')
		if flag1 and flag2:
			answer = ''
			for (index, value) in enumerate(dates):
				if index >= len(xianxing):
					break
				answer += value + u':' + xianxing[index] + u';'
		return answer, debug_info

	def parse_vr_food(self, data, answer, debug_info):
		'''解析vr食物
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'><span>', u'</span></a>')
		if flag:
			answer = u'、'.join(items)
		return answer, debug_info

	def parse_vr_meiju(self, data, answer, debug_info):
		'''解析vr枚举类型
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'<p class="enum-txt">', u'</p>')
		if flag:
			for (index, item) in enumerate(items):
				if index == 0:
					answer = comm.get_between(item, u'11008001_1_${rank}">', u'</a>')
				else:
					answer += u'、' + comm.get_between(item, u'11008001_1_${rank}">', u'</a>')
		return answer, debug_info

	def parse_vr_shiliao(self, data, answer, debug_info):
		'''解析vr健康食疗
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'<span>贴士', u'</div>')
		if flag:
			if debug_info['vr_class_id'] == '21376401':
				answer = u'贴士:' + comm.get_between(items[0], u'</span>', u'</h4>')
				flag, parts = comm.get_between_all(items[0], u'"sogou_vr_21376401_more_${rank}">', u'</a></p>')
				if flag:
					answer += u'。可以多吃'
					answer += u'、'.join(parts) + u'等。'
			elif debug_info['vr_class_id'] == '21377401':
				answer = u'贴士:' + comm.get_between(items[1], u'</span>', u'</h4>')
				flag, parts = comm.get_between_all(items[1], u'"sogou_vr_21377401_more_${rank}">', u'</a></p>')
				if flag:
					answer += u'。不要吃'
					answer += u'、'.join(parts) + u'等。'
		return answer, debug_info

	def parse_vr_map(self, data, answer, debug_info):
		'''解析vr地图
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if data.find('<url><![CDATA[') != -1:
			debug_info['url'] = comm.get_between(data, u'<url><![CDATA[', u']]></url>')
			if debug_info['query_type'] == 7:
				answer = u'我已经为你找到了地图搜索，开始使用吧，请戳[' + debug_info['url'] + u']'
			else:
				debug_info['priority_id'] = 'VR_map_2'
				answer = u'我也不知道呢，你可以用地图工具搜索一下哦。'
		return answer, debug_info

	def parse_vr_leader(self, data, answer, debug_info):
		'''解析vr各国领导人
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if data.find(u'<p class="txt-pstature">') != -1:
			answer = comm.get_between(data, u'<p class="txt-pstature">', u'</p>')
		return answer, debug_info

	def parse_vr_teshou(self, data, answer, debug_info):
		'''解析vr特别行政区长官
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		data = comm.get_between(data, u'<div class="vr-operation-right">', u'</div>')
		answer = comm.get_between(data, u'<p class="explanation">', u'</p>')
		answer += u'是' + comm.get_between(data, u'<h3>', u'</h3>')
		return answer, debug_info

	def parse_vr_menu(self, data, answer, debug_info):
		'''解析vr菜谱
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		items = data.split('\n')
		for item in items:
			if answer == '' or answer == None:
				answer = ''
			if item.find(u'<ul class="txt-panel">') != -1 and answer != '':
				answer += u'更多烹饪步骤请戳[' + debug_info['url'] + u']'
				break
			elif item.find(u'<url><![CDATA[') != -1:
				debug_info['url'] = comm.get_between(item, u'<url><![CDATA[', u']]></url>')
			elif item.find(u'<div class="t">') != -1:
				answer += comm.get_between(item, u'<div class="t">', u'</div>')
			elif item.find(u'<div class="con">') != -1:
				answer += comm.get_between(item, u'<div class="con">', u'</div>') + u'。'
		return answer, debug_info

	def parse_vr_car(self, data, answer, debug_info):
		'''解析vr汽车
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		query = debug_info['query']
		debug_info['details'] = u'汽车vr'
		content = u'<li>' + comm.get_between(data, u'<li class="price">', u'</ul>')
		flag, items = comm.get_between_all(content, u'<li>', u'</span>')
		if flag and len(items) == 5:
			if query.find(u'指导价') != -1 or query.find(u'参考价') != -1 or query.find(u'价格') != -1 or query.find(u'价钱') != -1 or query.find(u'多少钱') != -1:
				answer = items[0].replace(u'<span>', u'') + ' ' + items[1].replace(u'<span>', u'')
			elif query.find(u'变速箱') != -1:
				answer = items[2].replace(u'<span>', u'')
			elif query.find(u'排量') != -1:
				answer = items[3].replace(u'<span>', u'')
			elif query.find(u'油耗') != -1:
				answer = items[4].replace(u'<span>', u'')
		return answer, debug_info

	def parse_vr_xiehouyu(self, data, answer, debug_info):
		'''解析vr歇后语
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		content = comm.get_between(data, u'<ul class="twisters-list">', u'</ul>')
		flag, items = comm.get_between_all(content, u'<li>', u'</span>')
		if flag:
			answer = u'; '.join(items).replace(u' —— ', u'-').replace(u'<span>', u'')
		return answer, debug_info

	def parse_vr_xyxk(self, data, answer, debug_info):
		'''解析vr食物相克
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		content = comm.get_between(data, u'<p class="answer-recommend">', u'</div>')
		answer = comm.get_between_last(content, u'">', u'')
		return answer, debug_info

	def parse_vr_kefu(self, data, answer, debug_info):
		'''解析vr客服
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if debug_info['vr_class_id'] == '70030301':
			if data.find(u'<table class="vr_service">') == -1:
				item = comm.get_between(data, u'<strong', u'</strong>')
				answer = u'客服电话：' + comm.get_between(item, u'>', u'')
			else:
				content = comm.get_between(data, u'<table class="vr_service">', u'免费提交客服电话')
				flag, items = comm.get_between_all(content, u'<tr class=', u'</strong>')
				if flag:
					answer = ''
					for item in items:
						title = comm.get_between(item, u'<span class="servicetxt">', u'</span>')
						number = comm.get_between(item, u'<strong>', u'')
						if title != '' and number != '':
							answer += title + u':' + number + u'; '
						elif number != '':
							answer += number + u'; '
		elif debug_info['vr_class_id'] == '20009908':
			answer = comm.get_between(data, u'<label>客服电话: </label>', u'</div>')
		elif debug_info['vr_class_id'] == '70030302':
			answer = comm.get_between(data, u'<annotitle>', u'</annotitle>')
		return answer, debug_info

	def parse_vr_zgjm(self, data, answer, debug_info):
		'''解析vr周公解梦
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = ''
		flag, content = comm.get_between_all(data, u'<strong>', u'</p>')
		for (index, each) in enumerate(content):
			if index >= 5:
				break
			answer += str(index+1) + u'. ' + each.replace(u'</strong>', u':') + '\n'
		return answer, debug_info

	def parse_vr_exam(self, data, answer, debug_info):
		'''解析vr考试
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if debug_info['vr_class_id'] == '21199001':
			content = comm.get_between(data, u'<table class="vr-exam-table" style="display">', u'</table>')
			flag, items = comm.get_between_all(content, u'<th>', u'</a>')
			if flag:
				answer = ''
				for item in items:
					title = comm.get_between(item, u'', u':</th>')
					if title != '' and debug_info['query'].find(title) != -1:
						answer = comm.get_between_last(item, u'>', u'')
						break
		elif debug_info['vr_class_id'] == '20003643':
			flag, items = comm.get_between_all(data, u'<form', u'/>')
			if flag:
				answer = ''
				for item in items:
					title = comm.get_between(item, u'col1="', u'"')
					if title != '' and debug_info['query'].find(title) != -1:
						answer = comm.get_between(item, u'col0="', u'"')
						break
		return answer, debug_info

	def parse_vr_baoxian(self, data, answer, debug_info):
		'''解析vr五险一金
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if debug_info['vr_class_id'] == '21391901':
			flag, items = comm.get_between_all(data, u'<tr>', u'</tr>')
			if flag:
				answer = ''
				for (index, item) in enumerate(items):
					title = comm.get_between(item, u'">', u'</a>')
					if title != '':
						answer += str(index+1) + u'. ' + title + u':' + comm.get_between_last(item, u'<td>', u'</td>') + '\n'
		return answer, debug_info

	def parse_vr_olympic(self, data, answer, debug_info):
		'''解析vr奥运五环
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if debug_info['vr_class_id'] == '21342701':
			answer = comm.get_between(data, u'<p class="history">', u'</p>')
		return answer, debug_info

	def parse_vr_chengyu(self, data, answer, debug_info):
		'''解析vr成语
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'<span><a target=', u'</a></span>')
		if flag:
			answer = ''
			for item in items:
				answer += comm.get_between(item, u'">', u'') + u' '
		return answer, debug_info

	def parse_vr_chengyu2(self, data, answer, debug_info):
		'''解析vr词语成语(阿凡题)
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'<dl>', u'</dl>')
		if flag:
			answer = ''
			for item in items:
				answer += comm.get_between(item, u'<dt>', u'<') + comm.get_between(item, u'<dd>', u'<') + '\n'
		return answer, debug_info

	def parse_vr_chengyu3(self, data, answer, debug_info):
		'''解析vr词语成语(阿凡题)
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		content = comm.get_between(data, u'<p class="jyc-box">', '<div class="jyc-info">')
		flag, items = comm.get_between_all(content, u'">', u'</a>')
		if flag:
			answer = ' '.join(items)
		return answer, debug_info

	def parse_vr_poem_author(self, data, answer, debug_info):
		'''解析vr诗人
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		content = comm.get_between(data, u'<h3 class="vrTitle">', u'</h3>')
		answer = comm.get_between(content, u'">', u'</a>/') + comm.get_between(content, u'</a>/', u'')
		answer += u': ' + comm.get_between(data, u'<div class="poem-author">', u'</div>')
		return answer, debug_info

	def parse_vr_poem(self, data, answer, debug_info):
		'''解析vr诗词
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = comm.get_between(data, u'<h3 class="vrTitle"><span>', u'</span></h3>').strip()
		answer += u': ' + comm.get_between(data, u'<div class="next-sentence">', u'</div>').strip()
		return answer, debug_info

	def parse_vr_poem_all(self, data, answer, debug_info):
		'''解析vr描写某些事物的诗句
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		flag, items = comm.get_between_all(data, u'<h4>\n<span>', u'</p>')
		if flag:
			answer = ''
			for item in items:
				answer += comm.get_between(item, u'">', u'</a>').strip() + u' ' + comm.get_between(item, u'', u'</span>')
				answer += u': ' + comm.get_between(item, u'<p>', u'') + '\n'
		return answer, debug_info

	def parse_vr_jieri(self, data, answer, debug_info):
		'''解析vr节日由来
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = comm.get_between(data, u'<div class="brief-intro">', u'</div>')
		return answer, debug_info

	def parse_vr_gaofeng(self, data, answer, debug_info):
		'''解析vr世界高峰
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		content = comm.get_between(data, u'<p class="explanation">', u'</h3>')
		answer = comm.get_between(content, u'', u'</p>')
		answer += u': ' + comm.get_between(content, u'<h3>', u'')
		return answer, debug_info


parse_vr = ParseVR()
