#generate deepcoder data
import pickle
# TODO
from deepcoder_util import make_holey_deepcoder # this might be enough
from robustfill_util import basegrammar # TODO
from robustfill_util import sample_program, generate_IO_examples, timing # TODO

import time
from collections import namedtuple
#Function = namedtuple('Function', ['src', 'sig', 'fun', 'bounds'])
import sys
sys.path.append("/om/user/mnye/ec")
from grammar import Grammar, NoCandidates
from utilities import flatten

# TODO
from RobustFillPrimitives import RobustFillProductions, flatten_program, tprogram

from program import Application, Hole, Primitive, Index, Abstraction, ParseFailure
import math
import random
from type import Context, arrow, tint, tlist, UnificationFailure
from itertools import zip_longest, chain
from functools import reduce
import torch


class Datum():
	def __init__(self, tp, p, pseq, IO, sketch, sketchseq, reward, sketchprob):
		self.tp = tp
		self.p = p
		self.pseq = pseq
		self.IO = IO
		self.sketch = sketch
		self.sketchseq = sketchseq
		self.reward = reward
		self.sketchprob = sketchprob

	def __hash__(self): 
		return reduce(lambda a, b: hash(a + hash(b)), flatten(self.IO), 0) + hash(self.p) + hash(self.sketch)

Batch = namedtuple('Batch', ['tps', 'ps', 'pseqs', 'IOs', 'sketchs', 'sketchseqs', 'rewards', 'sketchprobs'])


def sample_datum(g=basegrammar, N=5, V=100, L=10, compute_sketches=False, top_k_sketches=100, inv_temp=1.0, reward_fn=None, sample_fn=None, dc_model=None):

	#sample a program:
	#with timing("sample program"):
	program = sample_program(g, max_len=L, max_string_size=V)  # TODO
	# if program is bad: return None  # TODO

	# find IO
	#with timing("sample IO:"):
	IO = generate_IO_examples(program, num_examples=N,  max_string_size=V)  # TODO
	if IO is None: return None
	IO = tuple(IO)
	# find tp
	tp = tprogram
	# TODO

	# find pseq
	pseq = tuple(flatten_program(program)) #TODO

	if compute_sketches:
		# find sketch
		grammar = basegrammar if not dc_model else dc_model.infer_grammar(IO)
		#with timing("make_holey"):
		sketch, reward, sketchprob = make_holey_deepcoder(program, top_k_sketches, grammar, tp, inv_temp=inv_temp, reward_fn=reward_fn, sample_fn=sample_fn) #TODO

		# find sketchseq
		sketchseq = tuple(flatten_program(sketch))
	else:
		sketch, sketchseq, reward, sketchprob = None, None, None, None

	return Datum(tp, program, pseq, IO, sketch, sketchseq, reward, sketchprob)


def grouper(iterable, n, fillvalue=None):
	"Collect data into fixed-length chunks or blocks"
	# grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
	args = [iter(iterable)] * n
	return zip_longest(*args, fillvalue=fillvalue)

def batchloader(size, batchsize=100, g=basegrammar, N=5, V=100, L=10, compute_sketches=False, dc_model=None, shuffle=True, top_k_sketches=20, inv_temp=1.0, reward_fn=None, sample_fn=None):
	if batchsize==1:
		data = (sample_datum(g=g, N=N, V=V, L=L, compute_sketches=compute_sketches, dc_model=dc_model, top_k_sketches=20, inv_temp=inv_temp, reward_fn=reward_fn, sample_fn=sample_fn) for _ in range(size))
		yield from (x for x in data if x is not None)
	else:
		data = (sample_datum(g=g, N=N, V=V, L=L, compute_sketches=compute_sketches, dc_model=dc_model, top_k_sketches=20, inv_temp=inv_temp, reward_fn=reward_fn, sample_fn=sample_fn) for _ in range(size))
		data = (x for x in data if x is not None)
		grouped_data = grouper(data, batchsize)

		for group in grouped_data:
			tps, ps, pseqs, IOs, sketchs, sketchseqs, rewards, sketchprobs = zip(*[(datum.tp, datum.p, datum.pseq, datum.IO, datum.sketch, datum.sketchseq, datum.reward, datum.sketchprob) for datum in group if datum is not None])
			yield Batch(tps, ps, pseqs, IOs, sketchs, sketchseqs, torch.FloatTensor(rewards) if any(r is not None for r in rewards) else None, torch.FloatTensor(sketchprobs) if any(s is not None for s in sketchprobs) else None)  # check that his works 


if __name__=='__main__':
	import time
	
	g = Grammar.fromProductions(RobustFillProductions(max_len=50, max_index=4))
	d = sample_datum(g=g, N=4, V=50, L=10, compute_sketches=True, top_k_sketches=100, inv_temp=1.0, reward_fn=None, sample_fn=None, dc_model=None)
	print(d.p)
	for i,o in d.IO:
		print("example")
		print(i)
		print(o)
	#loader = batchloader(600, g=g, batchsize=200, N=5, V=50, L=10, compute_sketches=True, dc_model=None, shuffle=True, top_k_sketches=10)

	# t = time.time()
	# for batch in loader:
	# 	print(time.time() - t)
	# 	print(batch.IOs[0])
	# 	print(batch.ps[0])

	# print(d)
	# if d is not None:
	# 	print(d.p)
	# 	print(d.IO)
	# 	print(d.sketch)
	# from itertools import islice
	# convert_source_to_datum("a <- [int] | b <- [int] | c <- ZIPWITH + b a | d <- COUNT isEVEN c | e <- ZIPWITH MAX a c | f <- MAP MUL4 e | g <- TAKE d f")

	# filename = 'data/DeepCoder_data/T2_A2_V512_L10_train_perm.txt'
	# train_data = 'data/DeepCoder_data/T3_A2_V512_L10_train_perm.txt'

	# test_data = ''

	# lines = (line.rstrip('\n') for i, line in enumerate(open(filename)) if i != 0) #remove first line

	# for datum in islice(batchloader([train_data], batchsize=1, N=5, V=128, L=10, compute_sketches=True, top_k_sketches=20, inv_temp=0.05), 30):
	# 	print("program:", datum.p)
	# 	print("sketch: ", datum.sketch)
		
	#path = 'data/pretrain_data_v1_alt.p'
	#make_deepcoder_data(path, with_holes=True, k=20)