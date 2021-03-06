

import os
import sys
import numpy
import pylab
from heapq import *

from btcsim import *

class BadMiner(Miner):
	chain_head_others = '*'
	privateBranchLen = 0
	
	def add_block(self, t_block):
		self.blocks[hash(t_block)] = t_block
		if (self.chain_head == '*'):
			self.chain_head = hash(t_block)
			self.chain_head_others = hash(t_block)
			self.mine_block()
			return
		
		if (t_block.miner_id == self.miner_id) and (t_block.height > self.blocks[self.chain_head].height):
			delta_prev = self.blocks[self.chain_head].height - self.blocks[self.chain_head_others].height
			self.chain_head = hash(t_block)
			self.privateBranchLen += 1
			if (delta_prev == 0) and (self.privateBranchLen == 2):
				self.announce_block(self.chain_head)
				self.privateBranchLen = 0
			self.mine_block()
		
		if (t_block.miner_id != self.miner_id) and (t_block.height > self.blocks[self.chain_head_others].height):
			delta_prev = self.blocks[self.chain_head].height - self.blocks[self.chain_head_others].height
			self.chain_head_others = hash(t_block)
			if delta_prev <= 0:
				self.chain_head = hash(t_block)
				self.privateBranchLen = 0
			elif delta_prev == 1:
				self.announce_block(self.chain_head)
			elif delta_prev == 2:
				self.announce_block(self.chain_head)
				self.privateBranchLen = 0
			else:
				iter_hash = self.chain_head
				# the temp is in case we get too far ahead (in case we have >51%)
				temp = 0
				if delta_prev >= 6: temp = 1
				while self.blocks[iter_hash].height != t_block.height + temp:
					iter_hash = self.blocks[iter_hash].prev
				self.announce_block(iter_hash)
			self.mine_block()
			

t = 0.0
event_q = []

# root block
seed_block = Block(None, 0, t, -1, 0, 1)


# set up some miners with random hashrate
numminers = 6
hashrates = numpy.random.exponential(1.0, numminers)
validationrate=1024*1024*1024

# setup very strong miner
attacker_strength = 0.30
hashrates[numminers-1] = 0.0
hashrates[numminers-1] = hashrates.sum() * (attacker_strength/(1.0 - attacker_strength))

hashrates = hashrates/hashrates.sum()

miners = []
for i in range(numminers):
	miners.append(Miner(i, hashrates[i] * 1.0/600.0,validationrate, 200*1024, seed_block, event_q, t))

# make the strong miner a bad miner
miners[i] = BadMiner(i, hashrates[i] * 1.0/600.0, validationrate,200*1024, seed_block, event_q, t)



# add some random links to each miner

for i in range(numminers):
	for k in range(4):
		j = numpy.random.randint(0, numminers)
		if i != j:
			latency = 0.020 + 0.200*numpy.random.random()
			bandwidth = 10*1024 + 200*1024*numpy.random.random()

			miners[i].add_link(j, latency, bandwidth)
			miners[j].add_link(i, latency, bandwidth)


# simulate some days of block generation
curday = 0
maxdays = 1*7*24*60*60
maxdays = 5*24*60*60
while t < maxdays:
	t, t_event = heappop(event_q)
	#print('%08.3f: %02d->%02d %s' % (t, t_event.orig, t_event.dest, t_event.action), t_event.payload)
	miners[t_event.dest].receive_event(t, t_event)
	
	if t/(24*60*60) > curday:
		print('day %03d' % curday)
		curday = int(t/(24*60*60))+1



# data analysis

pylab.figure()

cols = ['r-', 'g-', 'b-', 'y-']

mine = miners[0]
t_hash = mine.chain_head

rewardsum = 0.0
for i in range(numminers):
	miners[i].reward = 0.0

main_chain = dict()
main_chain[hash(seed_block)] = 1


itt=0

b={}

while t_hash != None:
	itt+=1
	t_block = mine.blocks[t_hash]
	
	if t_hash not in main_chain:
		main_chain[t_hash] = 1
	
	miners[t_block.miner_id].reward += 1
	rewardsum += 1
	
	if t_block.prev != None:
		pylab.plot([mine.blocks[t_block.prev].time, t_block.time], [mine.blocks[t_block.prev].height, t_block.height], cols[t_block.miner_id%4])
		print(itt)
		if not (t_block.miner_id%4 in b):
			b[t_block.miner_id%4]=0

		b[t_block.miner_id%4]+=1
	
	t_hash = t_block.prev
print(b)
pylab.xlabel('time in s')
pylab.ylabel('block height')
pylab.draw()

pylab.figure()

pylab.plot([0, numpy.max(hashrates)*1.05], [0, numpy.max(hashrates)*1.05], '-', color='0.4')
print(numminers)
for i in range(numminers):
	#print('%2d: %0.3f -> %0.3f' % (i, hashrates[i], miners[i].reward/rewardsum))
	pylab.plot(hashrates[i], miners[i].reward/rewardsum, 'k.')
pylab.plot(hashrates[i], miners[i].reward/rewardsum, 'rx')

pylab.xlabel('hashrate')
pylab.ylabel('reward')



pylab.figure()
orphans = 0
for i in range(numminers):
	print(i)
	for t_hash in miners[i].blocks:
		if t_hash not in main_chain:
			orphans += 1
		# draws the chains
		if miners[i].blocks[t_hash].height > 1:
			cur_b = miners[i].blocks[t_hash]
			pre_b = miners[i].blocks[cur_b.prev]
			pylab.plot([hashrates[pre_b.miner_id], hashrates[cur_b.miner_id]], [pre_b.height, cur_b.height], 'k-')

pylab.ylabel('block height')
pylab.xlabel('hashrate')
pylab.ylim([0, 100])

print('Orphaned blocks: %d (%0.3f)' % (orphans, orphans/mine.blocks[mine.chain_head].height))
print('Average block height time: %0.3f min' % (mine.blocks[mine.chain_head].time/(60*mine.blocks[mine.chain_head].height)))




pylab.draw()
pylab.show()

