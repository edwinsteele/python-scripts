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
METRICS = (RESPONSE_SIZE, RESPONSE_TIME)


def handle_aggregation(agg):
    for metric in METRICS:
        if agg and agg[metric].count > 0:
            print "%s %s (%s readings): %s (5th), %s (median), %s (95th)" % \
                  (agg[metric].aggregation_datetime,
                   metric,
                   agg[metric].count,
                   agg[metric].fifth,
                   agg[metric].median,
                   agg[metric].ninety_fifth)


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


def filtered_interpreted_follow(follower, match_url):
    for line in follower:
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
        this_request_period = request_fields[REQUEST_DATETIME].\
            replace(minute=0, second=0, microsecond=0)
        for metric in metrics:
            if this_request_period == last_request_period:
                metrics[metric].append(request_fields[metric])
                aggregated_metrics = {}
            else:
                # Flush the metric value for the previous time period
                aggregated_metrics[metric] = Aggregation(
                    last_request_period,
                    len(metrics[metric]),
                    *fifth_median_ninetyfifth(metrics[metric]))
                # Start the metric value for the new time period
                metrics[metric] = [request_fields[metric]]

        request_fields = yield aggregated_metrics
        last_request_period = this_request_period


logfile = open(LOG)
f = follow(logfile, True)
request_fields_from_log = filtered_interpreted_follow(f, URL_TO_MATCH)
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
