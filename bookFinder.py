
from BeautifulSoup import BeautifulSoup
import logging, os, re, string, sys, urllib
from optparse import OptionParser

# TODO - filter by type book, dvd, audio, (reference book?)
# TODO - penrith has max of 10 items per page. need to go look at the
#         subsequent pages
# TODO - BMCC looks like it only shows the first 5 copies of a book in the
#         page that we use, though there may be more copies. See Harry Potter
#         first match (the one where Katoomba has a "not found" copy)
# TODO - enumerate Library holding states, so that they appear consistently
#         from library to library
# TODO - only show if it's available and on the shelf
# TODO - bookmooch, including whether they'll send to australia
# TODO - allow grouping by book, or by library
# TODO - translate entitydefs into readable characters in non-html output
#         (see second Harry Potter match)
# TODO - Penrith has loaned books in the date format of 'Due: 2010-12-07'
#         but BMCC has '02/12/2010' - consistify
# TODO - give an option to show the books that matched the title but not
#         the author

class LibraryHolding:
    ON_SHELF="On shelf"
    ON_LOAN="On loan"
    LOST="Lost"
    IN_REPAIR="Being repaired"
    IN_RESERVE="Reserve only"
    HELD="Awaiting collection"

    def __init__(self, libraryLocation, holdingStatus, holdingDetails):
        self.libraryLocation = libraryLocation
        self.holdingStatus = holdingStatus
        self.holdingDetails = holdingDetails

    def renderAsText(self):
        if self.libraryLocation is None:
            return "%s (%s)" % (self.holdingStatus, self.holdingDetails)
        elif self.holdingDetails:
            return "At %s (%s %s)" % \
                (self.libraryLocation, self.holdingStatus, self.holdingDetails)
        else:
            return "At %s (%s)" % (self.libraryLocation, self.holdingStatus)

class BookMatch:
    def __init__(self, matchTitle):
        self.matchTitle = matchTitle
        self.holdingList = []

class BaseBookFinder:

    def __init__(self, bookTitle, bookAuthor):
        self.bookTitle = bookTitle
        self.bookAuthor = bookAuthor
        self.bookMatchList = []
        self.rejectedMatchCount = 0

    def renderAsText(self):
        # Meh... shouldn't be here, should be on a results object or something
        for bookMatch in self.bookMatchList:
            print bookMatch.matchTitle
            for holding in bookMatch.holdingList:
                print "- %s" % holding.renderAsText()

class BMCCFinder(BaseBookFinder):
    shortName = "BMCC"
    matchesPerPage = 50 # Adjustable
    urlTemplate=('http://www1.bmcc.nsw.gov.au/ipac20/ipac.jsp?'
        'session=12R06M981M943.97122&menu=search&aspect=advanced&'
        'npp=%s&ipp=20&spp=20&profile=spwd&ri=&term=&index=.GW&x=0&'
        'y=0&aspect=advanced&term=%s&index=.TW&term=&index=.SK&term=&'
        'index=.AW&term=&index=.NW&term=&index=.SW&term=&index=.SE&'
        'ultype=&uloper=%%3D&ullimit=&ultype=&uloper=%%3D&ullimit=&sort=')
    NO_HOLDING_DETAILS="&nbsp;"
    NO_MATCH_REPLY="Sorry, could not find anything matching"
    DEFAULT_HOLDING_STATUS="Unknown Holding Status"

    # It's possible that "Lost" and "Not found" are different, but the book
    #  isn't available so there's little point in differentiating
    holdingStatusMapping = {
        "Checked In":LibraryHolding.ON_SHELF,
        "Lost":LibraryHolding.LOST,
        "Checked out":LibraryHolding.ON_LOAN,
        "In Repair":LibraryHolding.IN_REPAIR,
        "Not Found":LibraryHolding.LOST,
        "Transit Request":LibraryHolding.HELD,
        "At withdrl":LibraryHolding.HELD,
                "Item being held":LibraryHolding.HELD
    }

    def getMatchCount(self):
        matchNumberPlaceholder=self.soup.find("a", "normalBlackFont2")
        if matchNumberPlaceholder:
            if matchNumberPlaceholder.text == self.NO_MATCH_REPLY:
                return 0
            else:
                return int(self.soup.find("a", "normalBlackFont2").b.text)
        else:
            # Single record returned
            return 1

    def executeSearch(self):
        logging.debug("Executing search at: %s" % self.urlTemplate % \
                (self.matchesPerPage, urllib.quote_plus(self.bookTitle), ))
        f = urllib.urlopen(self.urlTemplate % \
                (self.matchesPerPage, urllib.quote_plus(self.bookTitle), ))
        self.soup = BeautifulSoup(f.read())

        #with open("/Users/esteele/Documents/Code/bmccFull.html", "r") as f:
        #      self.soup = BeautifulSoup(f.read())

        # Table of matches e.g. searching for "The Hobbit" by Tolkien
        multipleMatchTable = self.soup.findAll("table", \
                {"class":"tableBackground", "style":"0", "height":"100%"})
        # Single match e.g. "The guns of august" by Barbara Tuchman
        singleMatchTable = self.soup.find("table", \
                {"class":"tableBackground", "cellpadding":"3", \
                "cellspacing":"0", "width":"100%", "border":"0"})
        if multipleMatchTable:
            possibleMatchTables = multipleMatchTable
        elif self.soup.find(text=self.NO_MATCH_REPLY + " "):
            # No matches. Note that no matches also has the tableBackground
            #  below, so we need this check
            # Note also that the A tag that contains the no match reply has
            #  a trailing space that we need to specify to get the match
            possibleMatchTables = []
        else:
            possibleMatchTables = [singleMatchTable]

        for possibleMatchTable in possibleMatchTables:
            if self.soup.find("table", {"class":"tableBackgroundHighlight", \
                        "cellpadding":"0", "cellspacing":"0", "width":"100%", \
                        "border":"0", "bgcolor":"#EEEECC"}):
                # Single Match
                titleString = self.soup.find("a", {"class":"smallAnchor", \
                        "href":re.compile(".*uindex=TL.*")})["title"]
            else:
                # Multiple Match
                titleString = possibleMatchTable.find("img", \
                        {"name":re.compile("bkey[0-9]+")}).parent.parent.parent.findAll("a", "mediumBoldAnchor")[0].text

            if self.soup.find("a", {"class":"smallAnchor", \
                        "href":re.compile(".*search=AL.*")}):
                authorString = self.soup.find("a", {"class":"smallAnchor", \
                        "href":re.compile(".*search=AL.*")}).text
            else:
                authorEnclosure=possibleMatchTable.find("a", "normalBlackFont1")
                # Video cassettes don't have an author, and so the italic
                #  tag doesn't exist. Let's set the authorString to be the
                #  empty string so that it doesn't match.
                if authorEnclosure.i:
                    authorString = possibleMatchTable.find("a", \
                                        "normalBlackFont1").i.text
                else:
                    authorString = ""

            if len(self.bookAuthor.split()) > 1:
                # Construct a regex that matches an author with a first and
                #  second name even if the library reverses the names e.g.
                #  "firstname secondname" should match an author of
                #  "firstname secondname", "secondname, firstname" or
                #  "secondname firstname"
                authorRe = '(%s)[, ]+(%s)' % \
                        (string.join(self.bookAuthor.split(),'|'), \
                        string.join(self.bookAuthor.split(),'|'))
            else:
                # book author is a single word (no whitespace)
                authorRe = self.bookAuthor

            if re.search(authorRe, authorString, re.I):
                logging.debug("[ MATCH ] AuthorString: %s TitleString: %s" % \
                        (authorString, titleString))
                self.createBookMatch(titleString, possibleMatchTable)
            else:
                self.rejectedMatchCount = self.rejectedMatchCount + 1
                logging.debug("[NO MATCH] AuthorString: %s TitleString: %s" % \
                        (authorString, titleString))

    def createBookMatch(self, matchTitle, matchTable):
        bookMatch = BookMatch(matchTitle)
        holdingLibraryRows = matchTable.findAll("tr", {"height":15})
        if len(holdingLibraryRows) > 5:
            # Need to look at the details. BMCC only shows the first five
            #  holdings on the detail page. Show what we have anyway...
            #  at least for the moment
            logging.warning("MORE THAN 5 MATCHES... look at the details page")

        for holdingLibraryRow in holdingLibraryRows:
            libraryLocation = holdingLibraryRow.findAll("a", \
                                        {"title":"Item Information"})[0].text
            holdingStatus = holdingLibraryRow.findAll("a", \
                                        {"title":"Item Information"})[3].text
            holdingStatusStandardised = self.holdingStatusMapping.get(holdingStatus, self.DEFAULT_HOLDING_STATUS)

            if holdingStatusStandardised == LibraryHolding.ON_LOAN:
                # BMCC provides the library that loaned the book, even though
                #  it may not necessarily be returned there. Consistify and
                #  thus omit it.
                returnDetails = holdingLibraryRow.findAll("a", \
                                        {"title":"Item Information"})[4].text
                returnDetails = "Due: %s" % returnDetails
                libraryLocation = None
            else:
                returnDetails = ""

            bookMatch.holdingList.append(LibraryHolding(libraryLocation, \
                        holdingStatusStandardised, returnDetails))

        self.bookMatchList.append(bookMatch)

class PenrithOpacFinder(BaseBookFinder):
    shortName = "Penrith"
    matchesPerPage = 10 # Not adjustable, as far as I can tell
    baseUrl='http://opac.penrithcity.nsw.gov.au/opacs/'
    searchUrl= baseUrl + 'BasicSearch?status=0&collection=all&from=BasicSearch'

    DEFAULT_HOLDING_STATUS="Unknown Holding Status"

    # It's possible that "Lost" and "Not found" are different, but the book
    #  isn't available so there's little point in differentiating
    holdingStatusMapping = {
        "On Shelf":LibraryHolding.ON_SHELF,
        "On Loan":LibraryHolding.ON_LOAN,
        "Reserve Notified":LibraryHolding.IN_RESERVE,
        "Reserve Local":LibraryHolding.IN_RESERVE,
        "Reserve Other":LibraryHolding.IN_RESERVE,
    }


    def getMatchCount(self):
        matchNumberPlaceholder=self.soup.find("font", {"face":"arial", \
                "size":3, "color":"#547CBB"})
        if matchNumberPlaceholder:
            return int(re.findall('\d+', matchNumberPlaceholder.text)[0])
        else:
            # Should never get here
            return "Should never get here"

    def executeSearch(self):
        postDict = {"searchwords": self.bookTitle, "searchcode":1, \
                        "pageno":1, "status":0, "collection":"all"}
        f=urllib.urlopen(self.searchUrl, urllib.urlencode(postDict))
        logging.debug("Executed search at: %s" % f.geturl())
        self.soup = BeautifulSoup(f.read())

        #with open("/Users/esteele/Documents/Code/penrithOpac.html", "r") as f:
        #      self.soup = BeautifulSoup(f.read())

        possibleMatches = self.soup.findAll("tr", \
                {"bgcolor":re.compile("#F[C5]F[C5]F[C5]")})
        for possibleMatch in possibleMatches:
            titleString = possibleMatch.find("a", \
                {"href":re.compile("^TitleDetails")}).text
            authorEnclosure = possibleMatch.find("a", \
                {"href":re.compile("^BasicSearch")})
            # Video cassettes don't have an author, and so the italic tag
            #  doesn't exist. Let's set the authorString to be the emptystring
            #  so that it doesn't match.
            if authorEnclosure:
                authorString = possibleMatch.find("a", \
                        {"href":re.compile("^BasicSearch")}).text
            else:
                authorString = ""

            if len(self.bookAuthor.split()) > 1:
                # Construct a regex that matches an author with a first and
                #  second name even if the library reverses the names e.g.
                #  "firstname secondname" should match an author of 
                #  "firstname secondname", "secondname, firstname" or
                #  "secondname firstname"
                authorRe = '(%s)[, ]+(%s)' % \
                        (string.join(self.bookAuthor.split(),'|'), \
                         string.join(self.bookAuthor.split(),'|'))
            else:
                # book author is a single word (no whitespace)
                authorRe = self.bookAuthor

            if re.search(authorRe, authorString, re.I):
                self.createBookMatch(titleString, possibleMatch)
            else:
                self.rejectedMatchCount = self.rejectedMatchCount + 1
                logging.debug("[NO MATCH] AuthorString: %s TitleString: %s" % \
                                (authorString, titleString))

    def createBookMatch(self, matchTitle, matchSoupContainer):
        bookMatch = BookMatch(matchTitle)
        f = urllib.urlopen(self.baseUrl + \
                string.replace(matchSoupContainer.find("a", \
                {"href":re.compile("^TitleDetails")})["href"], " ", "+"))
        logging.debug("Executed title detail at: %s" % f.geturl())
        titleDetailSoup = BeautifulSoup(f.read())

        for holdingLibraryRow in titleDetailSoup.find("table", \
                {"bgcolor":"#006666"}).findAll("tr", {"bgcolor":"#ffffff"}):
            volumeJunk, holdingLibrary, holdingStatus = \
                map(lambda enclosingTag: enclosingTag.b.text, \
                        holdingLibraryRow.findAll("font", {"color":"#CD0000"}))
            holdingStatusStandardised = self.holdingStatusMapping.get(holdingStatus, self.DEFAULT_HOLDING_STATUS)
            # No return details available at Penrith, unless they're a part
            #  of the holding status
            returnDetails = ""
            # When on loan, the library field is "On Loan", and the holding
            #  status field is the return date
            if holdingLibrary == "On Loan":
                holdingLibrary=None
                holdingStatusStandardised=LibraryHolding.ON_LOAN
                returnDetails = holdingStatus

            bookMatch.holdingList.append(LibraryHolding(holdingLibrary, \
                        holdingStatusStandardised, returnDetails))
        self.bookMatchList.append(bookMatch)


# --title "The Gulag Archipelago" --author "solzhenitsyn"
# --title "Charles Kingsford-Smith" --author "Peter Fitzsimons"
# --title "Harry Potter and the Deathly Hallows" --author "Rowling"
# --title "The Hobbit" --author "Tolkien"
# --title "Hunt for Red October" --author "Clancy"
# --title "The White Spider" --author "Heinrich Harrer"

def main():

    logging.basicConfig(level=logging.INFO)
    sourceToFinderDict = {"bmcc":BMCCFinder, "penrith":PenrithOpacFinder}

    bailout=False
    parser = OptionParser()
    prog = os.path.basename(sys.argv[0])
    parser.epilog = """e.g. %s -s penrith -t "Harry Potter and the Goblet of Fire" -a Rowling
e.g. %s -s penrith -t "Kingsford-Smith" -a "Peter Fitzsimons"
e.g. %s -s penrith,bmcc -t "The Gulag Archipelago" -a solzhenitsyn
""" % (prog, prog, prog)
    # Some of these actually should be positional arguments and not options
    #  given they're not actually optional!
    parser.add_option("-a", "--author", dest="author",
            help="Author to search for")
    parser.add_option("-t", "--title", dest="title",
            help="Title to search for")
    parser.add_option("-f", "--file", dest="inputFile",
            help="File containing title and author pairs")
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
            help="Output debug messages during execution")
    parser.add_option("-m", "--matchesonly", dest="matchesonly", 
            action="store_true",
            help="Only show results where there is a match")
    parser.add_option("-s", "--source", dest="sourceList", action="append",
            type="choice", choices=sourceToFinderDict.keys(),
            help="Source Library to search ('penrith' and 'bmcc' are the only valid options currently)")

    (options, args) = parser.parse_args()

    # Parse this option before any others, so debug logging is visible asap
    if options.debug:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.debug("Using debug level logging")

    logging.debug("Options: %s Args: %s" % (options, args))
    if not options:
        parser.print_help()
        bailout=True
    if (options.author or options.title) and options.inputFile:
        parser.error("options -a and -t must not be used with -f")
        bailout=True
    if not options.author and not options.inputFile:
        parser.error("option -a: missing author")
        bailout=True
    if not options.title and not options.inputFile:
        parser.error("option -t: missing title")
        bailout=True
    if not options.sourceList:
        parser.error("option -s: missing source(s)")
        bailout=True

    if bailout:
        sys.exit(2)

    bookList=[]
    if options.inputFile:
        with open(options.inputFile, "r") as f:
            bookLines=f.readlines()

        """
        Book lines have the following format:
        opt double quote, words (title), opt double quote, opt space,
          hyphen, opt space, words (author), opt space,
          opt left bracket + freetext + opt right bracket
        """
        bookLineRe=re.compile('"?(?P<titleStr>[\w \'-:;,\.]+)"? ?- "?(?P<authorStr>[\w \.&]+[\w\.&])')
        for bookLine in bookLines:
            mo = bookLineRe.match(bookLine)
            if mo:
                logging.debug("Title:%s. Author:%s." % \
                        (mo.group("titleStr"), mo.group("authorStr")))
                bookList.append((mo.group("titleStr"), mo.group("authorStr")))
            else:
                logging.debug("No match found in line:%s" % bookLine)

    else:
        bookList.append((options.title, options.author))

    for source in options.sourceList:
        finderClass = sourceToFinderDict[source]
        for title, author in bookList:
            summaryStr = "Searching %s for %s (%s)" % (finderClass.shortName, \
                                title, author)
            logging.debug("Searching %s for %s (%s)" % (finderClass.shortName,\
                                title, author))
            finderInstance = finderClass(title, author)
            finderInstance.executeSearch()

            matchCount = finderInstance.getMatchCount()

            if matchCount > finderInstance.matchesPerPage:
                logging.warn("Number of matches (%s) exceeds those visible in one page (%s) - MISSING RESULTS" % (matchCount, finderInstance.matchesPerPage))

            if matchCount - finderInstance.rejectedMatchCount == 0:
                if options.matchesonly:
                    summaryStr = ""
                else:
                    summaryStr = "%s - No matches found" % summaryStr

            elif matchCount - finderInstance.rejectedMatchCount == 1:
                summaryStr = "%s - found 1 match" % summaryStr
            else:
                summaryStr = "%s - found %d matches" % (summaryStr, matchCount - finderInstance.rejectedMatchCount)

            if options.matchesonly:
                if finderInstance.rejectedMatchCount == 1:
                    summaryStr = "%s , discarding 1 match where title matches but author doesn't match." % summaryStr
                elif finderInstance.rejectedMatchCount > 1:
                    summaryStr = "%s, discarding %d matches where title matches by author doesn't match." % (summaryStr, finderInstance.rejectedMatchCount)
            else:
                summaryStr = "%s." % summaryStr

            if summaryStr:
                print summaryStr

            finderInstance.renderAsText()

    sys.exit(3)

main()
