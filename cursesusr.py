#!/usr/bin/env python3
from termcube.cube import Cube, ScrambleGenerator
from termcube.simulator import Simulator
from termcube.turn import TurnSequence

from collections import namedtuple
from sys import exit
from time import time
import curses
import datetime

class Solve(namedtuple('Solve', ['time', 'penalty', 'tags', 'scramble'])):
	def totaltime(self):
		if self.penalty == 'DNF':
			return self.time
		return self.time + self.penalty
	
	@staticmethod
	def formattime(time):
		if time == None:
			return None
		return '%.2f' % time if time < 60 else '%d:%05.2f' % divmod(time, 60)
	
	def __str__(self):
		timestr = Solve.formattime(self.time)
		if self.penalty == 0:
			return timestr
		elif self.penalty == 2:
			return '%s (+2)' % timestr
		elif self.penalty == 'DNF':
			return '%s (DNF)' % timestr

class Timer(Simulator):
	def __init__(self, size = 3, inspection = 15, usingtags = True, random = True, length = -1):
		super(Timer, self).__init__(size)
		self.inspection = inspection
		self.usingtags = usingtags
		self.random = random
		self.length = length if not random else None
	
	def __call__(self, scr):
		self.initialize(scr)
		solves = []
		solvenumber = 1
		best = worst = sessionavg = curravg5 = bestavg5 = None
		qy, qx = self.q.getmaxyx()
		self.q.addstr(qy//2 -1, (qx - len("Initializing..."))//2, "Initializing...")
		self.q.refresh()
		
		with ScrambleGenerator(self.size, self.random, self.length) as scrambler:
			while True:
				#Print statistics
				stats = ["Solve number : %d" % solvenumber,
						 "Best : %s" % Solve.formattime(best),
						 "Worst : %s" % Solve.formattime(worst),
						 "Session Avg : %s" % Solve.formattime(sessionavg),
						 "Current Avg 5 : %s" % Solve.formattime(curravg5),
						 "Best Avg 5 : %s" % Solve.formattime(bestavg5)]
				self.r.clear()
				for i in range(min(len(stats), self.r.getmaxyx()[0])):
					self.r.addstr(i, (self.r.getmaxyx()[1] - len(stats[i])) // 2, stats[i])
				self.r.refresh()
				
				#Scramble
				self.reset()
				self.apply('x')
				scramble = next(scrambler)
				self.apply(scramble)

				#Print Cube and Scramble
				self.printcube(self.w)
				self.w.refresh()
				qy, qx = self.q.getmaxyx()
				self.q.addstr(qy//2 - 1, (qx - len(str(scramble)))//2, str(scramble))

				#Throw out key presses during scramble wait
				self.q.nodelay(1)
				while self.q.getch() >= 0:
					pass
				self.q.nodelay(0)

				#Inspect
				self.q.nodelay(0)
				self.q.getch()
				self.q.nodelay(1)
				penalty = self.countdown(self.q, self.inspection)
				
				#Solve
				time = self.countup(self.q)
				solves.append(Solve(time, penalty, None, scramble))
				self.q.getch()
				
				#Print solve times
				self.e.clear()
				for i in range(min(solvenumber, self.e.getmaxyx()[0])):
					timestr = 'Solve %d: %s' % (solvenumber - i, solves[-i-1])
					self.e.addstr(i, (self.e.getmaxyx()[1] - len(timestr))//2, timestr)
				self.e.refresh()
				
				#Update statistics
				if best == None:
					best = worst = time
					sessionavg = 1
				
				if time < best:
					best = time
				if time > worst:
					worst = time
				sessionavg = (sessionavg*(solvenumber - 1) + time) / solvenumber
				if solvenumber >= 5:
					curravg5 = Timer.avg5(solves)
					if bestavg5 == None or curravg5 < bestavg5:
						bestavg5 = curravg5 
				solvenumber += 1

	@staticmethod
	def avg5(arr):
		if len(arr) <= 0:
			return 0
		elif len(arr) < 5:
			return sum(s.totaltime() for s in arr)/len(arr)
		else:
			return sum(s.totaltime() for s in arr[-5::])/5

	def countdown(self, scr, inspection = 15.0):
		scr.clear()
		maxqy, maxqx = scr.getmaxyx()
		
		ret = 0
		start = time()
		c = -1
		while c < 0 or c == curses.KEY_RESIZE:
			scr.clear()
			delta = inspection + start - time()
			if delta > 0:
				s = '%.2f' % delta
			elif delta > -2:
				s = '+2'
				ret = 2
			else:
				s = 'DNF'
				ret = 'DNF'
			
			scr.addstr(maxqy//2 - 1, (maxqx - len(s))//2, s)
			scr.refresh()
			c = scr.getch()
			curses.napms(10)
		curses.beep()
		
		return ret

	def countup(self, scr):
		scr.clear()
		maxqy, maxqx = scr.getmaxyx()
		
		start = time()
		c = -1
		while True:
			if c == curses.KEY_RESIZE:
				self.resize()
			elif c == 27:
				return -1
			elif c > 0:
				break
			
			total = time() - start
			s = Solve.formattime(total)
			scr.addstr(maxqy//2 - 1, (maxqx - len(s))//2, s)
			scr.refresh()
			c = scr.getch()
			curses.napms(10)
		
		return time() - start

	def initialize(self, scr):
		super(Timer, self).initialize(scr)
		self.resize()
		self.q.nodelay(1)
		self.w.nodelay(1)
		self.e.nodelay(1)
		self.r.nodelay(1)
	
	def resize(self):
		maxy, maxx = self.scr.getmaxyx()
		height = maxy//5
		self.q = curses.newwin(height, maxx, 0, 0)
		self.w = curses.newwin(4*height, maxx//2, height, 0)
		self.e = curses.newwin(2*height, maxx//2, 3*height, maxx//2)
		self.r = curses.newwin(2*height, maxx//2, height, maxx//2)
		self.printcube(self.w)
		self.refresh()
	
	def refresh(self):
		for s in [self.q, self.w, self.e, self.r]:
			s.refresh()
	
	def recolor(self, color):
		for s in [self.q, self.w, self.e, self.r]:
			s.bkgd(color)
			s.bkgdset(color)
			s.refresh()

from sys import argv
def main(scr, size = 3, inspection = 15, usingtags = True, random = True, length = -1):
	Timer(size, inspection, usingtags, random, length)(scr)

curses.wrapper(main, 3 if len(argv) < 2 else argv[1])#, size, inspection, usingtags, random, length)
