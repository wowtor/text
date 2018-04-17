#!/usr/bin/env python

import sys
import time

TIME_UNITS = [
    ('s', 60),
    ('m', 60),
    ('h', 24),
    ('d', None),
  ]

__metaclass__ = type


class LogRegel():
  def __init__(self, msg=None, checkpoints=None, **kw):
    self.prevlen = 0

    self.f = sys.stdout
    self.have_tty = None
    for key in kw:
      if key == 'file':
        self.f = kw[key]
      elif key == 'tty':
        self.have_tty = kw[key]
      else:
        raise ValueError('illegal argument: '+key)

    if self.have_tty is None:
      self.have_tty = self.f in [ sys.stdout, sys.stderr ] and self.f.isatty()

    if msg is not None:
      self.start(msg, checkpoints)

  def write(self, msg):
    if self.prevlen > 0:
      self.f.write('\r')

    self.f.write(msg)
    self.f.write(' ' * (self.prevlen - len(msg)))
    self.f.flush()

    self.prevlen = len(msg)

  def start(self, msg, checkpoints=None):
    self.checkpoints = checkpoints
    self.ccount = 0
    self.msg = msg
    self.start_time = time.time()
    self.last_checkpoint = self.start_time
    if self.have_tty:
      self.write(self.msg)
    else:
      self.f.write(self.msg)
      self.f.flush()

  def increaseCheckpoints(self, n):
    self.checkpoints += n

  def checkpoint(self, count=1, msg=None, position=None):
    self.ccount += count
    if position is not None:
        self.ccount = position

    if not self.have_tty:
      pass
    elif self.checkpoints is None:
      logmsg = '%s%s' % (self.msg, '.'*self.ccount)
      if msg is not None:
        logmsg += ' <%s>' % msg
      self.write(logmsg)
    else:
      cp_elapsed = time.time() - self.last_checkpoint
      if msg is not None or (self.ccount > 0 and cp_elapsed > .2):
        self.last_checkpoint = time.time()
        elapsed = self.last_checkpoint - self.start_time
        fraction = float(self.ccount) / self.checkpoints
        logmsg = '%s: %.0f%%' % (self.msg, fraction*100)
        if fraction > 0:
          remaining = (1-fraction) * elapsed / fraction
          for unit in TIME_UNITS:
            if unit[1] is None or remaining < unit[1]*3:
              logmsg += ' (T-%.0f%s)' % (remaining, unit[0])
              break
            else:
              remaining /= unit[1]
        if msg is not None:
          logmsg += ' <%s>' % msg
        self.write(logmsg)

  def done(self, msg=None):
    self.finish('OK', msg)

  def failed(self, msg):
    self.finish('Failed!', msg)

  def finish(self, status, msg=None):
    elapsed = time.time() - self.start_time
    append = ' -- %s' % msg if msg is not None else ''
    if self.have_tty:
      sep = '.'*self.ccount if self.checkpoints is None else ':'
      logmsg = '%s%s %s (%.3fs)%s' % (self.msg, sep, status, elapsed, append)
      self.write(logmsg)
      self.f.write('\n')
    else:
      self.f.write(': %s (%.3fs)%s\n' % (status, elapsed, append))
      self.f.flush()

if __name__ == "__main__":
  log = LogRegel('test', 1000000)
  for i in xrange(1000000):
    log.checkpoint()
  log.done()
