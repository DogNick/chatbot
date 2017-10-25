import time
import sys

class Trie(object):
	def __init__(self):
		self.tree = {}
		self.t2v = {}
		self.state = None

	def update(self, word, value):
		if self.t2v.has_key(word):
			self.t2v[word] = value

	# Compatible for strings and lists
	def add(self, word, value = None):
		if not word:
			return

		key = ''.join(word)
		if not value:
			value = key
		tree, self.t2v[key] = self.tree, value
		for c in word:
			if not tree.has_key(c):
				tree[c] = {}
			tree = tree[c]
		tree[''] = key

	# Compatible for strings and lists. Must be same as function add.
	def _search_head_longest(self, query):
		tree, result = self.tree, None
		for c in query:
			if tree.has_key(''):
				result = (tree[''], self.t2v[tree['']])
			if not tree.has_key(c):
				tree = {}
				break
			else:
				tree = tree[c]
		if tree.has_key(''):
			result = (tree[''], self.t2v[tree['']])
		return result

	def _search_head_all(self, query):
		tree, result = self.tree, []
		for c in query:
			if tree.has_key(''):
				result.append((tree[''], self.t2v[tree['']]))
			if not tree.has_key(c):
				tree = {}
				break
			else:
				tree = tree[c]
		if tree.has_key(''):
			result.append((tree[''], self.t2v[tree['']]))
		return result

	def search_first_longest(self, query):
		for i in xrange(len(query)):
			result = self._search_head_longest(query[i:])
			if result:
				return result

	def search_longest(self, query):
		result = None
		for i in xrange(len(query)):
			candidate = self._search_head_longest(query[i:])
			if candidate and (not result or len(candidate[0]) > len(result[0])):
				result = candidate
		return result

	def search_all(self, query):
		result, exist_keys = [], {}
		for i in xrange(len(query)):
			candidates = self._search_head_all(query[i:])
			for candidate in candidates:
				if not exist_keys.has_key(candidate[0]):
					exist_keys[candidate[0]] = 1
					result.append(candidate)
		return result

	def search_all_inorder(self, query):
		result = []
		for i in xrange(len(query)):
			res = self._search_head_all(query[i:])
			for itm in res:
				start, end = i, i + len(itm[0])
				result.append((start, end, itm))
		return result

	def greedy_match(self, query):
		lst = self.search_all_inorder(query)
		lst.sort(key = lambda x: x[1] - x[0])
		result = []
		while lst:
			itm = lst.pop()
			result.append(itm)
			start, end = itm[:2]
			new_lst = []
			for itm in lst:
				s, e = itm[:2]
				if s >= start and s < end or e > start and e <= end:
					continue
				new_lst.append(itm)
			lst = new_lst
		result.sort(key = lambda x: x[0])
		return result

	def query_replace(self, query):
		words = self.greedy_match(query)
		for start, end, (key, value) in words:
			query = query.replace(key, value, 1)
		return query

if __name__ == '__main__':
	pass
