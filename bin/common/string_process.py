#!/usr/bin/env python
#coding=utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


'''
	author: cuiyanyan

	功能:
		func1: 获取完整句子(处理summary截断)
		func2: 判断句子中是否包含特殊字符
		func3: 判断句子是否不包含中文
		func4: 只保留中文、英文和数字

		sub_func1: 判断字符串是否完整(判断summary截断的情况)
		sub_func2: 判断字符是否是句子分隔符
		sub_func3: 判断字符是否是逗号或英文句号
		sub_func4: 判断字符是否是半角或全角数字
		sub_func5: 判断字符是否是半角或全角字母
		sub_func6: 判断字符是否是汉字
		sub_func7: 判断字符是否是英文标点
		sub_func8: 判断字符是否是中文标点
		sub_func9: 判断字符是否是全角字符
		sub_func10: 判断字符是否是特殊字符

	note: 尽量使用半角字符
'''


def get_complete_sentence(sen, method='get'):
	'''
		func1
		功能: 获取完整的句子(处理summary截断)
		params:
			sen: 原句，编码Unicode
			method: get:只获取完整句子; replace:并替换其中的特殊字符
		return:
			flag: 操作代码，三个值(complete:不需要截断; need:需要截断; cannot:无法截断)
			result: 完整的句子，编码Unicode(去掉末尾省略号的句子，flag=cannot时，为空)
	'''
	result = ''
	flag, result = is_sentence_complete(sen)
	if flag == 'need':
		half = ''
		whole = ''
		new_answer = ''
		for ch in result:
			if is_end_of_sentence(ch):
				if half != '':
					whole += half
				new_answer += whole + ch
				whole = ''
				half = ''
			elif is_half_of_sentence(ch):
				whole += half
				if half != '':
					half = ch
			else:
				if method == 'replace':
					sc_flag, ch = is_special_character(ch)
				half += ch
		if half != '' and whole == '':
			whole = half
		if whole != '' and new_answer == '':
			new_answer = whole
		result = new_answer
	return flag, result


def is_contained_special_characters(sen):
	'''
		func2
		功能: 判断句子中是否包含特殊字符
		params:
			sen: 原句，编码Unicode
		return:
			flag: True:有特殊字符; False:无特殊字符
			result: 处理后的句子，编码Unicode
			character: 特殊字符，编码Unicode
	'''
	flag = False
	result = ''
	character = ''
	for ch in sen:
		sc_flag, ch = is_special_character(ch)
		if sc_flag:
			flag = True
			character = ch
			result = ''
		else:
			result += ch
	return flag, result, character


def is_not_contain_chinese(sen):
	'''
		func3
		功能: 判断句子是否不包含中文
		params:
			sen: 原句，编码Unicode
		return:
			flag: True:句子不包含中文; False:句子包含中文
	'''
	flag = True
	for ch in sen:
		if is_chinese(ch):
			flag = False
			break
	return flag


def delete_punctuation(sen):
	'''
		func4
		功能: 只保留中文、英文和数字
		params:
			sen: 原句，编码Unicode
		return:
			restring: 只保留中文、英文和数字的句子，编码Unicode
	'''
	restring = ''
	for ch in sen:
		if is_digital(ch) or is_alphabet(ch) or is_chinese(ch):
			restring += ch
	return restring


def is_sentence_complete(sen):
	'''
		sub_func1
		功能: 判断字符串是否完整(判断summary截断的情况)
		params:
			sen: 原句，编码Unicode
		return:
			flag: 三个值(complete:不需要截断; need:需要截断; cannot:无法截断)
			sen: 去掉末尾省略号的句子，编码Unicode(flag=cannot时，为空)
	'''
	flag = 'complete'
	end_flag = [u'...', u'．．．']
	for each in end_flag:
		pos = sen.rfind(each)
		if pos != -1:
			if pos + len(each) == len(sen):
				flag = 'need'
				sen = sen[0:pos]
			else:
				flag = 'cannot'
				sen = ''
			break
	return flag, sen


def is_end_of_sentence(ch):
	'''
		sub_func2
		功能: 判断字符是否是句子分隔符
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是句子分隔符; False:不是句子分隔符
	'''
	flag = False
	if ch == u'!' or ch == u'?' or ch == u'\u3002' or ch == u'\uff01' or ch == u'\uff1f':
		flag = True
	return flag


def is_half_of_sentence(ch):
	'''
		sub_func3
		功能: 判断字符是否是逗号或英文句号
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是逗号或英文句号; False:不是逗号或英文句号
	'''
	flag = False
	if ch == u',' or ch == u'\uff0c' or ch == u'.':
		flag = True
	return flag


def is_digital(ch):
	'''
		sub_func4
		功能: 判断字符是否是半角或全角数字
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是数字; False:不是数字
	'''
	flag = False
	if (ch >= u'\u0030' and ch <= u'\u0039') or (ch >= u'\uff10' and ch <= u'\uff19'):
		flag = True
	return flag


def is_alphabet(ch):
	'''
		sub_func5
		功能: 判断字符是否是半角或全角字母
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是字母; False:不是字母
	'''
	flag = False
	if (ch >= u'\u0041' and ch <= u'\u005a') or (ch >= u'\u0061' and ch <= u'\u007a') or (ch >= u'\uff21' and ch <= u'\uff3a') or (ch >= u'\uff41' and ch <= u'\uff5a'):
		flag = True
	return flag


def is_chinese(ch):
	'''
		sub_func6
		功能: 判断字符是否是汉字
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是汉字; False:不是汉字
	'''
	flag = False
	if ch >= u'\u4e00' and ch <= u'\u9fff':
		flag = True
	return flag


def is_english_punctuation(ch):
	'''
		sub_func7
		功能: 判断字符是否是英文标点
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是英文标点; False:不是英文标点
	'''
	flag = False
	if ch == u'~' or ch == u'!' or ch == u'?' or ch == u',' or ch == u'.' or ch == u':' or ch == u';' or ch == u'<' or ch == u'>' or ch == u'"' or ch == u'\'' or ch == u'(' or ch == u')' or ch == u'[' or ch == u']' or ch == u'{' or ch == u'}' or ch == u'`' or ch == u'@' or ch == u'#' or ch == u'$' or ch == u'%' or ch == u'^' or ch == u'&' or ch == u'|' or ch == u'\\' or ch == u'/' or ch == '+' or ch == u'-' or ch == u'*' or ch == u'=' or ch == u'_' or ch == u' ':
		flag = True
	return False


def is_chinese_punctuation(ch):
	'''
		sub_func8
		功能: 判断字符是否是中文标点
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是中文标点; False:不是中文标点
			ch: 纠正后的字符
	'''
	flag = False
	if ch == u'\xb7' or ch == u'\u2022':							#外国人名中间的点
		ch = u''
		flag = True
	elif ch == u'\uff5e' or ch == u'\u301c':						# ～
		ch = u'。'
		flag = True
	elif ch == u'\u2026':											#中文省略号
		flag = True
	elif ch == u'\uff01' or ch == u'\uff1f':						# ！ ？
		flag = True
	elif ch == u'\uff0c' or ch == u'\u3002':						# ， 。
		flag = True
	elif ch == u'\u3001' or ch == u'\uff1a' or ch == u'\uff1b':		# 、 ： ；
		flag = True
	elif ch == u'\u300a' or ch == u'\u300b':						# 《 》
		flag = True
	elif ch == u'\u201c' or ch == u'\u201d':						#双引号
		flag = True
	elif ch == u'\u2018' or ch == u'\u2019':						#单引号
		flag = True
	elif ch == u'\uff08' or ch == u'\uff09':						#小括号
		flag = True
	elif ch == u'\u3010' or ch == u'\u3011':						#中括号
		flag = True
	elif ch == u'\uff5b' or ch == u'\uff5d':						#大括号
		flag = True
	elif ch == u'\xb0' or ch == u'\u2103':							# ° ℃
		flag = True
	return flag, ch


def is_full_character(ch):
	'''
		sub_func9
		功能: 判断字符是否是全角字符
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是全角字符; False:不是全角字符
			ch: 纠正后的字符
	'''
	flag = False
	if ch == u'\uff02' or ch == u'\uff07':							#全角双引号，单引号
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\uff20' or ch == u'\uff03':						# ＠ ＃
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\uffe5':											# ￥
		flag = True
	elif ch == u'\uff05' or ch == u'\uff06':						# ％ ＆
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\uff5c' or ch == u'\uff3c' or ch == u'\uff0f':		# ｜ ＼ ／
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\uff0b' or ch == u'\uff0d':						# ＋ －
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\xd7':												# ×
		ch = u'*'
		flag = True
	elif ch == u'\uff1d' or ch == u'\uff0e':						# ＝ 全角.
		ch = unichr(ord(ch) - 65248)
		flag = True
	elif ch == u'\u2014' or ch == u'\u3000':						#全角下划线 全角空格
		ch = u'_'
		flag = True
	elif ch == u'\ue7ff' or ch == u'\uf348' or ch == u'\uf469' or ch == u'\uf4aa' or ch == u'\uf525' or ch == u'\uf601' or ch == u'\uf602' or ch == u'\uf604' or ch == u'\uf60d' or ch == u'\uf614' or ch == u'\uf618' or ch == u'\uf620' or ch == u'\uf62d':	#全角空白字符
		ch = u''
		flag = True
	return flag, ch


def is_special_character(ch):
	'''
		sub_func10
		功能: 判断字符是否是特殊字符
		params:
			ch: 一个字符，编码Unicode
		return:
			flag: True:是特殊字符; False:不是特殊字符
			ch: 纠正后的字符
	'''
	flag = False
	if is_digital(ch):
		return flag, ch
	elif is_alphabet(ch):
		return flag, ch
	elif is_chinese(ch):
		return flag, ch
	elif is_english_punctuation(ch):
		return flag, ch
	elif ch == u'\n':
		return flag, ch
	else:
		cp_flag, ch = is_chinese_punctuation(ch)
		if cp_flag:
			return flag, ch
		fc_flag, ch = is_full_character(ch)
		if fc_flag:
			return flag, ch
		ch = u''
		flag = True
	return flag, ch


if __name__ == '__main__':
	querys = [
			u'好漂亮啊...',
			u'就找点快乐的事来做嘛! 我要是心情不好,就找个空旷的地方大叫,或大哭一场,之后一切又恢复正常的! 其实你要学会记性不好,把烦恼忘了,就想一觉醒来,知道自...',
			u'我要是心情不好,就找个空旷的地方大叫,或大哭一场,之后一切...',
			u'我是女的.从小极内向.别人叫我哑巴 9岁没了爹.所以更自卑.怕别人看不起. 所以怕和别人对视.走路时连头都不扭. 别人在背后说:走路不看人好象欠她三百两银子 最大的弱...',
			u'how old are you',
			u'88拜',
			u'从卫生角度讲，鸡精对人体是有害的，在烹调时，如果加入过多鸡精，则会导致人体在短时间内摄取过量的谷氨酸钠，超过机体代谢能力，直接危害人体健康，重则引起食物中毒，甚至致癌。<p>当味精摄入过多时，过多的抑制性神经递质还会抑制人体的下丘脑分泌促甲状腺释放激素，妨碍骨骼发育，对儿童的影响尤为显着。在动物实验中发现，幼小的小老鼠、小鸡受味精的伤害最严重，会破坏脑神经和视神经。<p>当食用味精过多，超过机体的代谢能力时，还会导致血液中谷氨酸含量增高，限制人体对钙、镁、铜等必需矿物质的利用。...',
			u'鸡精不是从鸡身上提取的，它是在味精的基础上加入助鲜的核苷酸制成的！总的来说，味精和鸡精实际上是同一类东西，只是鸡精的味道要丰富一些罢了。<p>鸡精吃多了会怎么样？从卫生角度讲，鸡精对人体是有害的，在烹调时，如果加入过多鸡精，则会导致人体在短时间内摄取过量的谷氨酸钠，超过机体代谢能力，直接危害人体健康，重则引起食物中毒，甚至致癌。<p>当味精摄入过多时，过多的抑制性神经递质还会抑制人体的下丘脑分泌促甲状腺释放激素，妨碍骨骼发育，对儿童的影响尤为显着。在动物实验中发现，幼小的小老鼠...',
			u'从卫生角度讲，鸡精对人体是有害的，在烹调时，如果加入过多鸡精，则会导致人体在短时间内摄取过量的谷氨酸钠，超过机体代谢能力，直接危害人体健康，重则引起食物中毒，甚至致癌。<p>当味精摄入过多时，过多的抑制性神经递质还会抑制人体的下丘脑分泌促甲状腺释放激素，妨碍骨骼发育，对儿童的影响尤为显着。在动物实验中发现，幼小的小老鼠、小鸡受味精的伤害最严重，会破坏脑神经和视神经。<p>当食用味精过多，超过机体的代谢能力时，还会导致血液中谷氨酸含量增高，限制人体对钙、镁、铜等必需矿物质的利用。．．．',
			u'李白(701年-762年) ,字太白,号青莲居士,又号“谪仙人”,是唐代伟大的浪漫主义诗人,被后人誉为“诗仙”,与杜甫并称为“李杜”,为了与另两位诗人李商隐与杜牧即“小李杜”区别,杜甫与李白又合称“大李杜”。其人爽朗大方,爱饮酒作诗,喜交友。 李白深受黄老列庄思想影响,有《李太白集》传世,诗作中多以醉时写的,代表作有《望庐山瀑布...',
			u'李白(701年-762年) ,字太白...杜甫与李白又合称“大李杜”。',
			u'鸟为什么会飞呢?首先,鸟类的身体外面是轻而温暖的羽毛,羽毛不仅具有保温作用,而且使鸟类外型呈流线形,在空气中运动时受到的阻力最小,有利于飞翔,飞行时,...',
			u'灰兔子的眼睛是灰色的,白兔子的眼睛是透明的。那为什么我们看到小白兔的眼睛是红色的呢?这是因为白兔眼睛里的血丝反射了外界光线,透明的眼睛就显出红色。”我似懂非懂...'
		]
	for query in querys:
		flag, result = get_complete_sentence(query)
		print '>>>>>>'
		print 'query:', query.encode('utf-8')
		print 'result:', result.encode('utf-8')
		print 'flag:', flag
		print '\n\n'
	while True:
		print '******'
		raw = raw_input('ch:')
		print 'raw:', raw
		ch = str(raw).decode('utf-8')
		print 'raw2:', ch
		flag = is_chinese_punctuation(ch)
