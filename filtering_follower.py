import time
import os
import shlex
import datetime

__author__ = 'esteele'

# Sample logs obtained from
#  http://docs.splunk.com/Documentation/Splunk/latest/Tutorial/GetthesampledataintoSplunk

NO_VALUE = None
STILL_AGGREGATING = None


def fifth_median_ninetyfifth(sequence):
    sequence.sort()
    return sequence[int(len(sequence) * 0.05)], \
        sequence[int(len(sequence) * 0.5)], \
        sequence[int(len(sequence) * 0.95)]


def follow(fd, from_start, timeout_secs=5):
    secs_since_last_line = 0
    if from_start:
        fd.seek(0, os.SEEK_SET)
    else:
        fd.seek(0, os.SEEK_END)

    while secs_since_last_line < timeout_secs:
        line = fd.readline()
        if not line:
            time.sleep(1)
            secs_since_last_line += 1
            continue
        else:
            secs_since_last_line = 0
            yield line
    else:
        print "Timeout on file %s" % (fd.name,)


def filtered_interpreted_follow(fd, from_start, match_url):
    for line in follow(fd, from_start):
        fields = shlex.split(line)
        # GET /flower_store/enter_order_information.screen HTTP/1.1
        request_url = fields[4].split(" ")[1]
        if request_url != match_url:
            continue

        response_size_bytes = int(fields[6])
        response_time_usecs = int(fields[9])
        # [13/Apr/2013:23:58:10]
        request_datetime = datetime.datetime.strptime(fields[3],
                                                      "[%d/%b/%Y:%H:%M:%S]")
        yield request_datetime, response_size_bytes, response_time_usecs


def aggregate_by_hour():
    response_sizes = []
    request_date_hour = None
    last_request_date_hour = count = fifth = median = ninety_fifth = None

    while True:
        request_datetime, response_size_bytes, response_time_usecs = \
            yield last_request_date_hour, count, fifth, median, ninety_fifth
        last_request_date_hour = request_date_hour
        # Nerf the minutes, seconds and micros so that we're just looking at
        # hourly times. Could perhaps use datetime.resolution
        request_date_hour = request_datetime.replace(minute=0, second=0, microsecond=0)
        if request_date_hour == last_request_date_hour:
            response_sizes.append(response_size_bytes)
            count = fifth = median = ninety_fifth = STILL_AGGREGATING
        else:
            if response_sizes:
                fifth, median, ninety_fifth = fifth_median_ninetyfifth(response_sizes)
                count = len(response_sizes)

            response_sizes = [response_size_bytes]


URL_TO_MATCH = "/flower_store/enter_order_information.screen"
BASE_LOG_DIRECTORY = "/Users/esteele/Downloads/Sampledata/"
LOG = BASE_LOG_DIRECTORY + "apache1.splunk.com/access_combined.log"

logfile = open(LOG)
request_fields_from_log = filtered_interpreted_follow(logfile, True, URL_TO_MATCH)
aggregator = aggregate_by_hour()
aggregator.send(None)

for line_fields in request_fields_from_log:
    request_date_hour, count, fifth, median, ninety_fifth = aggregator.send(line_fields)
    if count != STILL_AGGREGATING:
        print "%s (%s readings): %s (5th), %s (median), %s (95th)" % (request_date_hour, count, fifth, median, ninety_fifth)
else:
    request_date_hour, count, fifth, median, ninety_fifth = aggregator.send((datetime.datetime.max, None, None))
    print "%s (%s readings): %s (5th), %s (median), %s (95th)" % (request_date_hour, count, fifth, median, ninety_fifth)
    print "Final reading done"


# Must do aggregator.send((None, None, None)) to flush the last set of values
