#coding=utf8

from accessor import *


point24_file = os.path.join(curr_dir, '../../data/24points/all24')


class Point24(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			begin = time.time()
			self.all_solutions = {}
			self.p_24points = re.compile(u'二十四点|算24点|算出24点|算24|算出24')
			self.number_m = {
					u'一':1, u'二':2, u'三':3, u'四':4, u'五':5, u'六':6, u'七':7, u'八':8, u'九':9, u'十':10, u'十一':11, u'十二':12, u'十三':13,
					u'1':1, u'2':2, u'3':3, u'4':4, u'5':5, u'6':6, u'7':7, u'8':8, u'9':9, u'10':10, u'11':11, u'12':12, u'13':13,
					u'A':1, u'a':1, u'J':11, u'j':11, u'Q':12, u'q':12, u'K':13, u'k':13, u'一十一':11, u'一十二':12, u'一十三':13
			}
			try:
				for line in open(point24_file, 'r'):
					digits, solution = line.rstrip().split('\t')
					self.all_solutions[digits] = solution
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [points24] [items=%d] [cost=%sms]' % (len(self.all_solutions), cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_number(self, query, params):
		number = []
		isvalid = True
		connect_word = 0
		segs = params.get('seg', [])
		for seg in segs:
			if seg[0] in Point24.rsc().number_m:
				number.append(Point24.rsc().number_m[seg[0]])
			elif seg[0] == u'和':
				connect_word += 1
			else:
				pos = seg[0].find(u'和')
				if pos == 0:
					if seg[0][1:] in Point24.rsc().number_m:
						number.append(Point24.rsc().number_m[seg[0][1:]])
						connect_word += 1
				elif pos > 0:
					if seg[0][0:pos] in Point24.rsc().number_m:
						number.append(Point24.rsc().number_m[seg[0][0:pos]])
						connect_word += 1
		if len(number) != 4 or connect_word < 2:
			isvalid = False
		number = sorted(number)
		return isvalid, number

	def parse_24points_result(self, query, params, answer, debug_info):
		isvalid, number = self.get_number(query, params)
		number = map(lambda x:str(x), number)
		digits = ' '.join(number)
		if isvalid:
			if Point24.rsc().all_solutions.has_key(digits):
				answer = u'答案是：' + Point24.rsc().all_solutions[digits]
				debug_info['digits'] = digits
				debug_info['status'] = 'OK'
			else:
				answer = u'这道题好像无解'
				debug_info['status'] = 'fatal error: no key for %s' % (digits)
		else:
			answer = u'本汪好像没听清楚'
			debug_info['status'] = 'not four valid number'
		detlog.info('[accessor_INFO] [24points] [query=%s] [digits=%s] [status=%s]' % (query.encode('utf-8'), digits, debug_info['status']))
		return answer, debug_info

	def get_points24_result(self, query, params, debug_info):
		answer = None
		if Point24.rsc().p_24points.search(query) != None:
			connect_num = 0
			pos = query.find(u'和')
			while pos != -1:
				connect_num += 1
				pos = query.find(u'和', pos+1)
			if connect_num > 2:
				match = Point24.rsc().p_24points.search(query).group(0)
				new_query = query[0:query.find(match)]
				answer, debug_info = self.parse_24points_result(new_query, params, answer, debug_info)
			else:
				debug_info['status'] = 'less connect word'
		else:
			debug_info['status'] = 'no 24points intention'
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {'from':self.acc_name}
		try:
			rets = self.get_points24_result(query, params, debug_info)
		except Exception, e:
			debug_info['status'] = 'error, ' + str(e)
			exclog.error('\n%s' % (traceback.format_exc(e)))
		if rets == []:
			rets = [(None, debug_info)]
		raise gen.Return(rets)

	@gen.coroutine
	def test(self):
		source = ""
		while True:
			print '>>>>>>>>>>>>>>>>'
			query = raw_input('query:').decode("utf-8")
			begin = time.time()
			query = get_query_correction(query, source)
			params = preprocessing(query, source)
			print json.dumps(params, ensure_ascii=False)
			results = yield self.run(query, params)
			answer = results[0][0]
			debug_info = results[0][1]
			end = time.time()
			print 'answer:' + str(answer).encode('utf-8')
			print 'debug_info:' + json.dumps(debug_info, ensure_ascii=False)
			print 'cost:' + str(round((end-begin)*1000, 2)) + 'ms'
			print '\n\n'


if __name__ == '__main__':
	from preprocessing import *
	conf = Config("dev", True, "develop")
	point24 = Point24(conf)
	point24()

