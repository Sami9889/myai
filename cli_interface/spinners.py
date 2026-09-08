from __future__ import annotations
import itertools, sys
class Spinner:
    def __init__(self,label='working'): self.label=label; self.frames=itertools.cycle('|/-\\'); self.active=False
    def start(self)->None:self.active=True
    def tick(self)->None:
        if self.active: sys.stderr.write('\r'+self.label+' '+next(self.frames)); sys.stderr.flush()
    def stop(self)->None:
        if self.active: sys.stderr.write('\r'+' '* (len(self.label)+4)+'\r'); sys.stderr.flush(); self.active=False
