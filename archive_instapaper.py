import os
import pprint
import subprocess
import stat
import colorama
from pyinstapaper.instapaper import Instapaper


# ARCHIVE_LOCATION = "/Users/esteele/Documents/ArchivedArticles"
ARCHIVE_LOCATION = "/Users/esteele/Library/Mobile\
        Documents/com~apple~CloudDocs/Articles"
INSTAPAPER_ARTICLE_TEMPLATE = "https://www.instapaper.com/read/%s"

need_manual_archiving = []
retried_files = []


def get_env_variable(var_name):
    """ Get the environment variable or return exception """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s env variable" % var_name
        raise RuntimeError(error_msg)


def title_to_filename(title):
    title = title.replace(":", "_")\
                 .replace("&", "_")\
                 .replace(" ", "-")\
                 .replace("\\", "_")\
                 .replace("'", "_")\
                 .replace('"', "_")\
                 .replace(r"/", "_")\
                 .replace("?", "_")
    return "%s.pdf" % (title,)


def main():
    colorama.init(autoreset=True)
    instapaper = Instapaper(get_env_variable("INSTAPAPER_API_KEY"),
                            get_env_variable("INSTAPAPER_API_SECRET"))
    instapaper.login(get_env_variable("INSTAPAPER_USERNAME"),
                     get_env_variable("INSTAPAPER_PASSWORD"))

    if not os.path.exists(ARCHIVE_LOCATION):
        os.mkdir(ARCHIVE_LOCATION)

    # Get the 10 latest instapaper bookmarks for the given account and do
    # something with the article text
    bookmarks = instapaper.get_bookmarks('starred', 500)
    for bookmark in bookmarks:
        filename = title_to_filename(bookmark.title)
        archived_bookmark_location = os.path.join(ARCHIVE_LOCATION, filename)
        if os.path.exists(archived_bookmark_location):
            print(colorama.Fore.GREEN +
                  "Already retrieved: %s (%s)" % (bookmark.title,
                                                  archived_bookmark_location))
        else:
            print(colorama.Fore.CYAN +
                  "Retrieving %s to %s" % (bookmark.url,
                                           archived_bookmark_location))
            ret_code = subprocess.call([
                "wkhtmltopdf",
                bookmark.url,
                archived_bookmark_location])
            if ret_code != 0:
                print(colorama.Fore.MAGENTA +
                      "Failed to retrieve article: %s. Trying with "
                      "--load-error-handling ignore" % (bookmark.url,))
                ret_code = subprocess.call([
                    "wkhtmltopdf",
                    "--load-error-handling",
                    "ignore",
                    bookmark.url,
                    archived_bookmark_location])
                if ret_code != 0:
                    print(colorama.Fore.RED +
                          "Failed to retrieve article: %s after retry. "
                          "Giving up." % (bookmark.url,))
                else:
                    print(colorama.Fore.YELLOW +
                          "Retry of article %s complete." %
                          archived_bookmark_location)
                    retried_files.append(archived_bookmark_location)

            else:
                print(colorama.Fore.GREEN +
                      "OK")

            file_size = os.stat(archived_bookmark_location)[stat.ST_SIZE]
            if file_size < 20000:
                print(colorama.Fore.RED +
                      "Article %s is likely bad. Removing." %
                      archived_bookmark_location)
                os.remove(archived_bookmark_location)
                need_manual_archiving.append((
                    bookmark.url,
                    archived_bookmark_location))

    print "Need manual archiving:"
    pprint.pprint(need_manual_archiving)
    print "Retried: %s" % (retried_files,)


if __name__ == "__main__":
    main()
