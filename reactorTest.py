__author__ = 'esteele'

from twisted.internet import reactor
import time


def print_time():
    print "Current time is", time.strftime("%H:%M:%S")

def block():
    print "sleeping for 3 secs"
    time.sleep(10)

def stop_reactor():
    print "Stopping reactor"
    reactor.stop()


reactor.callLater(1, print_time)
reactor.callLater(2, block)
reactor.callLater(3, print_time)
reactor.callLater(4, print_time)
reactor.callLater(5, stop_reactor)

print "Running the reactor..."
reactor.run()
print "Reactor stopped."
