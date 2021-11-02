from __future__ import division 
from __future__ import print_function
import math
import time
import re
import mysql.connector
from os import curdir, sep

from nltk.stem.porter import PorterStemmer
import operator
import urlparse
import json

from newQueryAuxiliary import query_tokenizer
from newQueryAuxiliary import postings_query_maker
from newQueryAuxiliary import relevance_query_maker


from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

config = {
	'user': 'root',
	# 'password': '#Akhil123',
	'host': '127.0.0.1',
	'database': 'infer',
	# 'raise_on_warnings': True,
	'use_pure': False,
	'auth_plugin': 'mysql_native_password'
}

dbConnector = mysql.connector.connect(**config)		
c = dbConnector.cursor()

table_name_1 = 'matrix'
table_name_2 = 'docvectors'
stemmer = PorterStemmer()

def searchList(user_input):
	# Query tokenization
	print('user_input: ', user_input)
	query_tokens = query_tokenizer(user_input, stemmer)
	query_length = len(query_tokens)
	# Postings retrieval
	result = []
	query, t = postings_query_maker(table_name_1, query_tokens, query_length)
	c.execute(query, t)
	rows = c.fetchall()

	# If any results are obtained:
	if (len(rows) > 0):
		# Creating lists to store postings.
		result_or = []
		result_and = []
		for w in rows:
			result_and.append(str(w[0]).split(','))
			result_or.extend(str(w[0]).split(','))
		# Transforms result_and from a list of lists into a list of elements
		# of intersection of all the lists
		result_and = list(set.intersection(*map(set, result_and)))

		relevance = {}

		# If at least 1 result with all query tokens is found
		if (len(result_and) > 0):
			final_postings = result_and
			print("\nResults containing all the search terms:\n")
		else:
			final_postings = result_or
			print("\nHere are some search results containings some of the search terms\n")
		
		# Obtaining Relevance information for each result
		for w in final_postings:
			doc_name = "doc" + str(w)
			relevance[doc_name] = 0
			
			query, t = relevance_query_maker(table_name_2, doc_name, query_tokens, query_length)

			c.execute(query, t)
			rows = c.fetchall()

			relevance[doc_name] = rows[0][0]

		# Sorting results by relevance
		relevance = sorted(relevance.items(), key = operator.itemgetter(1), reverse = True)

		# Retrieving & printing results
		for tok, rel in relevance:
			query = "SELECT * FROM docnames WHERE docno = %s"
			c.execute(query, (tok, ))
			rows = c.fetchall()
			#print_string = "%-10s %-23s %-45s " + CMS_course_URL + "?id=%s"
			#print(print_string % str(rel), rows[0][1], rows[0][2], str(rows[0][3]))
			result.append(rows)
	else:
		print("\nNo relevant documents containing all the search terms\n")

		end_time = time.time()
		# print("\nresults obtained in " + str(end_time - start_time) + " secs")

	return result

class HandleRequests(BaseHTTPRequestHandler):
	def _return_file(self):
		f = open(curdir + sep + self.path, 'rb') #self.path has /test.html
		self.send_response(200)
		if self.path.endswith(".html"):
			self.send_header('Content-type', 'text/html')
		elif self.path.endswith(".css"):
			self.send_header('Content-type', 'text/css')
		elif self.path.endswith(".pdf"):
			self.send_header('Content-type', 'application/pdf')
		elif self.path.endswith(".png"):
			self.send_header('Content-type', 'image/png')
		self.end_headers()
		self.wfile.write(f.read())
		f.close()

	def _return_data(self):
		o = urlparse.urlparse(self.path)
		q = o.query.split('=')[1]
		result = searchList(q)
		json_string = json.dumps({
			"result": result
		})
		# print("json_string: ", json_string)
		self.wfile.write(json_string)


	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.send_header('Access-Control-Allow-Origin', "*")
		self.end_headers()

	def do_OPTIONS(self):
		self.send_response(200, "ok")
		self.send_header('Access-Control-Allow-Credentials', 'true')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")

	def do_GET(self):
		print('self.path? ', self.path)
		try:
			if self.path.endswith(".html") or self.path.endswith(".pdf") or self.path.endswith(".png") or self.path.endswith(".css"):
				self._return_file()
			else:
				self._set_headers()
				self._return_data()
			
		except IOError:
				self.send_error(404,'File Not Found: %s' % self.path)
			
	def do_POST(self):
		'''Reads post request body'''
		self._set_headers()
		content_len = int(self.headers.getheader('content-length', 0))
		post_body = self.rfile.read(content_len)
		self.wfile.write("received post request:<br>{}".format(post_body))

	def do_PUT(self):
		self.do_POST()

host = ''
port = 3000
print("Starting web server at port: ", port)
HTTPServer((host, port), HandleRequests).serve_forever()
