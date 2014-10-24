#!/usr/bin/env python
#-*- coding: utf8 *-*
__version__ = '0.1__24oct2014'


import sys
import os

this_folder	= os.path.dirname(os.path.realpath(__file__))


import operator
import time
import string
import subprocess

from KafNafParserPy import KafNafParser, Cterm, Cspan, Clp
from lib.token_matcher import token_matcher


def find_treetagger():
	'''
	This function tries to find the treetagger via 2 ways:
	1) Checking the TREE_TAGGER_PATH variable in the file ./lib/__init__.py
	2) Checking the environment variable TREE_TAGGER_PATH
   	'''
	path_to_treetagger = None
	try:
		from lib import TREE_TAGGER_PATH
		path_to_treetagger = TREE_TAGGER_PATH
	except:
		if 'TREE_TAGGER_PATH' in os.environ:
			path_to_treetagger = os.environ['TREE_TAGGER_PATH']
	
	return path_to_treetagger
	



def loadMapping(mapping_file):
	map={}
	filename = os.path.join(os.path.dirname(__file__),mapping_file)
	fic = open(filename)
	for line in fic:
		fields = line.strip().split()
		map[fields[0]] = fields[1]
	fic.close()
	return map



if __name__=='__main__':
	this_folder = os.path.dirname(os.path.realpath(__file__))

	if sys.stdin.isatty():
			print>>sys.stderr,'Input stream required.'
			print>>sys.stderr,'Example usage: cat myUTF8file.kaf |',sys.argv[0]
			sys.exit(-1)


	input_obj = KafNafParser(sys.stdin)
	my_lang = input_obj.get_language()

	complete_path_to_treetagger = find_treetagger()
	if complete_path_to_treetagger is None:
		print>>sys.stderr,'Treetagger could not be found. You need to specify there treetagger is installed in 2 ways:'
		print>>sys.stderr,'\t1)Update the TREE_TAGGER_PATH variable in the file lib/__init__.py'
		print>>sys.stderr,'\t2_Update your TREE_TAGGER_PATH environment variable'
		sys.exit(0)
        
        
    # In the last version of treetagger all the names of commands have been change from X-utf to just X
    # /cmd/tree-tagger-english-utf8 ==> /cmd/tree-tagger-english
    # This could be a problem in case other version of treetagger is being used.
	if my_lang == 'en':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-english'
		mapping_file = this_folder +'/mappings/english.map.treetagger.kaf.csv'
		model = 'English models'
	elif my_lang == 'nl':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-dutch'
		mapping_file = this_folder +'/mappings/dutch.map.treetagger.kaf.csv'
		model = 'Dutch models'
	elif my_lang == 'de':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-german'
		mapping_file = this_folder +'/mappings/german.map.treetagger.kaf.csv'
		model = 'German models'
	elif my_lang == 'fr':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-french'
		mapping_file = this_folder +'/mappings/french.map.treetagger.kaf.csv'
		model = 'French models'
	elif my_lang == 'it':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-italian'
		mapping_file = this_folder +'/mappings/italian.map.treetagger.kaf.csv'
		model = 'Italian models'
	elif my_lang == 'es':
		treetagger_cmd = complete_path_to_treetagger+'/cmd/tree-tagger-spanish'
		mapping_file = this_folder +'/mappings/spanish.map.treetagger.kaf.csv'
		model = 'Spanish models'
	else: ## Default is dutch
		print>>sys.stderr,'Language',my_lang,'not supported by this wrapper'
		sys.exit(0)

	map_tt_to_kaf = loadMapping(mapping_file)


	## Create the input text for
	reference_tokens = []
	sentences = []
	prev_sent='-200'
	aux = []
	for token in input_obj.get_tokens():
		sent_id = token.get_sent()
		word = token.get_text()
		w_id = token.get_id()
		if sent_id != prev_sent:
			if len(aux) != 0:
				sentences.append(aux)
				aux = []
		aux.append((word,w_id))

		prev_sent = sent_id
	if len(aux)!=0:
		sentences.append(aux)


	num_term = 0 
	for sentence in sentences:
		#print>>sys.stderr,'Input sentnece:',sentence
		text = ' '.join(t.encode('utf-8') for t,_ in sentence)

		if not os.path.isfile(treetagger_cmd):
			print>>sys.stderr, "Can't find the proper tree tagger command: " +treetagger_cmd
			raise IOError(treetagger_cmd)
		try:
			tt_proc = subprocess.Popen(treetagger_cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		except Exception as e:
			print>>sys.stderr,str(e)

		out, err = tt_proc.communicate(text)

		#print>>sys.stderr,'Output treetagger',out, err
		data = {}
		new_tokens = []
		for line in out.splitlines():
			line = line.decode('utf-8')
			my_id = 't'+str(num_term)
			num_term += 1
			token,pos,lemma = line.strip().split('\t')
			pos_kaf = map_tt_to_kaf.get(pos,'O')

			if lemma=='<unknown>':
				lemma=token
				pos+=' unknown_lemma'
			if pos_kaf in ['N','R','G','V','A','O']:
				type_term = 'open'
			else:
				type_term = 'close'
			data[my_id] = (token,pos_kaf,lemma,type_term,pos)
			new_tokens.append((token,my_id))
		#tt_proc.terminate()

		mapping_tokens = {}

		token_matcher(sentence,new_tokens,mapping_tokens)
		new_terms = []
		terms_for_token = {}
		for token_new, id_new in new_tokens:
			token,pos_kaf,lemma,type_term,pos = data[id_new]
			ref_tokens = mapping_tokens[id_new]
			span = []
			#print token_new, id_new, ref_tokens
			for ref_token in ref_tokens:
				span.append(ref_token)
				if ref_token in terms_for_token:
					terms_for_token[ref_token].append(id_new)
				else:
					terms_for_token[ref_token] = [id_new]

			new_terms.append((id_new,type_term,pos_kaf,pos,lemma,span))


		#print terms_for_token
		not_use = set()
		for id_new,type_term,pos_kaf,pos,lemma,span in new_terms:
			#print not_use
			#print id_new
			if id_new not in not_use:
				new_lemma = ''
				for tokenid in span:
					if len(terms_for_token[tokenid]) > 1:
						new_lemma += (''.join(data[t][2] for t in terms_for_token[tokenid])).lower()
						not_use |= set(terms_for_token[tokenid])
				if new_lemma != '':
					lemma = new_lemma

				###############
				new_term = Cterm(type=input_obj.get_type())
				new_term.set_id(id_new)
				new_term.set_type(type_term)
				new_term.set_pos(pos_kaf)
				new_term.set_morphofeat(pos)
				new_term.set_lemma(lemma)
				term_span = Cspan()
				term_span.create_from_ids(span)
				new_term.set_span(term_span)
				input_obj.add_term(new_term)
	##End for each sentence

	my_lp = Clp()
	my_lp.set_name('Treetagger model'+model)
	my_lp.set_version(__version__)
	my_lp.set_timestamp()
	input_obj.add_linguistic_processor('term', my_lp)
	input_obj.dump(sys.stdout)


