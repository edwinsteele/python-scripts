#!/usr/bin/env python2.6
#
# This creates a more useable slashdot RSS feed, including:
# - links to the primary article
# - none of the sharing icons
# - no duplicates
#
# $Id: slashdotRssCreator.cgi 148 2012-03-15 19:22:13Z esteele $
#

import cgitb, datetime, re, sys, urllib2
cgitb.enable()

import PyRSS2Gen
from BeautifulSoup import BeautifulSoup
from pytz import timezone

class RSS2WithAtomExtension(PyRSS2Gen.RSS2):
    rss_attrs = {"version": "2.0", "xmlns:atom":"http://www.w3.org/2005/Atom"}
    def publish_extensions(self, handler):
        handler.startElement("atom:link", \
          {"href": "http://www.wordspeak.org/slashdotRssCreator.cgi", \
          "rel": "self", \
          "type":"application/rss+xml"})
        handler.endElement("atom:link")

f = urllib2.urlopen("http://slashdot.org")
slashdotSoup = BeautifulSoup(f.read())

#with open("/Users/esteele/Documents/Code/slashdot.html", "r") as f:
#  slashdotSoup = BeautifulSoup(f.read())

rssOutput = RSS2WithAtomExtension(
    title = "Slashdot",
    link = "http://slashdot.org",
    description = "Alt-RSS by Edwin",
    lastBuildDate = datetime.datetime.utcnow())

articleHeaders = slashdotSoup.findAll("span", id=re.compile('title-[0-9][0-9]*'))
articleBodies = slashdotSoup.findAll("div", id=re.compile('text-[0-9][0-9]*'))

# articleHeaders and articleBodies should be of equal lengths - nothing will break
#  if they're not, as the first StopIteration will end the loop, so let's not actually
#  make a test for that. If the headers and bodies don't agree it'll be obvious to
#  the consumer of the feed

articleHeaderIter = iter(articleHeaders)
articleBodiesIter = iter(articleBodies)

while 1:
    try:
        articleHeader = articleHeaderIter.next()
        articleBody = articleBodiesIter.next()
    except StopIteration:
        break

    mo = re.search("day (?P<monthDayStr>.*), @(?P<timeOfDayStr>[0-9:]+)(?P<amOrPm>[AP]M)", \
      articleHeader.find('span', "date").text)
    if mo:
        articleTime = datetime.datetime.strptime("%s %s %s %s" %
            (mo.group("monthDayStr"),
            mo.group("timeOfDayStr"),
            mo.group("amOrPm"),
            datetime.date.today().year), "%B %d %I:%M %p %Y")
    else:
        # make an obviously wrong datetime object if we don't match
        articleTime = datetime.datetime(1950, 1, 1, 0, 0, 0)

    articleTimeInUSEastern = articleTime.replace(tzinfo=timezone('US/Eastern'))

    rssOutput.items.append(PyRSS2Gen.RSSItem(
        title = articleHeader.find('a', "datitle").text,
        link = "http:%s" % (articleHeader.find("a", href=re.compile("slashdot\.org"))['href'],),
        description = str(articleBody),
        guid = "http:%s" % (articleHeader.find("a", href=re.compile("slashdot\.org"))['href'],),
        pubDate = articleTimeInUSEastern.astimezone(timezone('UTC'))))

print "Content-Type: application/rss+xml\n"
rssOutput.write_xml(sys.stdout)
