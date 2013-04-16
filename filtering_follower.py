import collections
import datetime
import os
import shlex
import time


# dictionaries will get better performance...
# see: http://stackoverflow.com/questions/2646157/what-is-the-fastest-to-access-struct-like-object-in-python
Aggregation = collections.namedtuple(
    "aggregation",
    ["aggregation_datetime", "count", "fifth", "median", "ninety_fifth"],
)

# Sample logs obtained from
#  http://docs.splunk.com/Documentation/Splunk/latest/Tutorial/GetthesampledataintoSplunk

URL_TO_MATCH = "/flower_store/enter_order_information.screen"
BASE_LOG_DIRECTORY = "/Users/esteele/Downloads/Sampledata/"
LOG = BASE_LOG_DIRECTORY + "apache1.splunk.com/access_combined.log"
RESPONSE_SIZE = "response_size"
RESPONSE_TIME = "response_time"
REQUEST_DATETIME = "request_datetime"


def handle_aggregation(agg):
    if agg and agg[RESPONSE_SIZE].count > 0:
        print "%s (%s readings): %s (5th), %s (median), %s (95th)" % \
              (agg[RESPONSE_SIZE].aggregation_datetime,
               agg[RESPONSE_SIZE].count,
               agg[RESPONSE_SIZE].fifth,
               agg[RESPONSE_SIZE].median,
               agg[RESPONSE_SIZE].ninety_fifth)


def fifth_median_ninetyfifth(sequence):
    if sequence:
        sequence.sort()
        return sequence[int(len(sequence) * 0.05)], \
            sequence[int(len(sequence) * 0.5)], \
            sequence[int(len(sequence) * 0.95)]
    else:
        # These values are undefined when the sequence is empty
        return [None, None, None]


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
        yield {REQUEST_DATETIME: request_datetime,
               RESPONSE_SIZE: response_size_bytes,
               RESPONSE_TIME: response_time_usecs
               }


def aggregate_by_hour():
    metrics = {RESPONSE_SIZE: [], RESPONSE_TIME: []}
    last_request_period = None
    aggregated_metrics = {}

    # We don't have any metrics yet but need to accept the first
    request_fields = yield aggregated_metrics

    while True:
        # Nerf the mins, secs & micros so we're just looking at hourly times.
        this_request_period = request_fields[REQUEST_DATETIME].replace(minute=0, second=0, microsecond=0)
        if this_request_period == last_request_period:
            metrics[RESPONSE_SIZE].append(request_fields[RESPONSE_SIZE])
            aggregated_metrics = {}
        else:
            # Flush the metrics for the previous time period
            fifth, median, ninety_fifth = \
                fifth_median_ninetyfifth(metrics[RESPONSE_SIZE])
            count = len(metrics[RESPONSE_SIZE])
            aggregated_metrics[RESPONSE_SIZE] = Aggregation(
                last_request_period, count, fifth, median, ninety_fifth)
            # Start the metrics for the new time period
            metrics[RESPONSE_SIZE] = [request_fields[RESPONSE_SIZE]]

        request_fields = yield aggregated_metrics
        last_request_period = this_request_period


logfile = open(LOG)
request_fields_from_log = filtered_interpreted_follow(logfile, True, URL_TO_MATCH)
aggregator = aggregate_by_hour()
aggregator.send(None)

for line_fields in request_fields_from_log:
    handle_aggregation(aggregator.send(line_fields))
else:
    # flush the last set of values
    handle_aggregation(aggregator.send({REQUEST_DATETIME: datetime.datetime.max,
                                        RESPONSE_SIZE: None,
                                        RESPONSE_TIME: None}))
    print "Final reading done"
