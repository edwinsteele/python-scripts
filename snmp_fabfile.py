import os
from fabric.api import env, local, parallel, task
from fabric.context_managers import cd, hide, quiet, warn_only
import fabric.colors
from hnmp import SNMP, SNMPError
import time

ACCESS_POINTS = ["ap-kitchen", "ap-bedroom"]


def retry_until_true(delay_secs=1):
    """Mostly pinched from https://wiki.python.org/moin/PythonDecoratorLibrary"""
    def dec(func):
        def f2(*args, **kwargs):
            rv = func(*args, **kwargs)
            while not rv:
                print(args[0]("retrying"))
                time.sleep(delay_secs)
                rv = func(*args, **kwargs)
            return rv
        return f2
    return dec


def do_stuff():
    print "do_stuff for %s" % (env.host_string,)


@retry_until_true(delay_secs=5)
def get_mac(c):
    with quiet():
        # Give the ARP cache a chance to be populated
        ping()
        result = local("arp %s" % (env.host_string,), capture=True)
    if "incomplete" in result.stdout or \
            "no entry" in result.stdout:
        return None
    elif "Unknown host" in result.stderr:
        return None
    else:
        return result.stdout.split(" ")[3]


def ping():
    local("ping -q -t 2 -c 1 %s" % (env.host_string,))


def get_print_colour():
    all_colours = ("blue", "green", "magenta", "red", "yellow", "cyan")
    return getattr(fabric.colors, all_colours[env.hosts.index(env.host_string)])
    # return all_colours[]


def mac_to_snmp_string(mac_addr):
    return ".".join([str(ord(i.upper())) for i in mac_addr])


def get_signal_strength(ap, mac_addr):
    BASE_OID = "1.3.6.1.4.1.63.501.3.2.2.1.6.17."
    try:
        snmp = SNMP(ap)
        oid = BASE_OID + mac_to_snmp_string(mac_addr)
        signal_strength = snmp.get(oid)
    except SNMPError:
        signal_strength = None

    return signal_strength


@task
def meta():
    colour = get_print_colour()
    mac = get_mac(colour)
    print(colour("MAC (%s) is %s" % (env.host_string, mac,)))
    while True:
        for access_point in ACCESS_POINTS:
            print(colour("%s signal strength: %s db" %
                         (access_point,
                          get_signal_strength(access_point, mac))))
        time.sleep(5)


