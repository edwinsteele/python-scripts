from datetime import datetime, timedelta
import itertools
import requests
import conf

BASE_URL = "http://realtime.grofsoft.com/tripview/realtime?routes=%s&type=dtva"


class Trip(object):
    def __init__(self, trip_id):
        self.trip_id = trip_id
        self.start_time_str = "unknown"
        self.start_time_timedelta = timedelta.max
        self.start_loc_int = -1
        self.start_loc_str = "unknown"
        self.location = "unknown"
        self.alert = None
        self.offset_tuples = []

    def populate_estimated_arrival_times(self):
        start_time = self.start_time_timedelta
        # If we can't find a transit time, return results that have not
        #  chance of being in the schedule. Subtract 1 from max so we can
        #  attempt to perform usual calculations without overflow
        min_transit, max_transit = conf.transit_times.get(
            self.start_loc_str,
            (timedelta.min, timedelta.max - timedelta(days=1)))
        self.est_arrival_earliest = start_time + min_transit
        self.est_arrival_latest = start_time + max_transit

    def is_current(self):
        """Arrives at departure station in the future"""
        n = datetime.now()
        return timedelta(hours=n.hour, minutes=n.minute) \
            < self.est_arrival_latest

    def arrives_in_departure_window(self):
        """Arrives at departure station in the window"""
        return \
            self.est_arrival_earliest > conf.FIRST_DEPARTURE_TIME and \
            self.est_arrival_latest < conf.LAST_DEPARTURE_TIME

    def estimate_delay_at_boarding_station(self):
        possible_delay_tuples = list(itertools.dropwhile(
            lambda x: x[0] < self.est_arrival_earliest, self.offset_tuples))
        #print "Est Arrival: %s - %s, Possible delays: %s" %\
        #      (self.est_arrival_earliest,
        #       self.est_arrival_latest,
        #       list(possible_delay_tuples),)
        # The first delay number will be close enough, so let's use that
        if possible_delay_tuples:
            return possible_delay_tuples[0][1]
        else:
            return 0

    def delay_description(self):
        estimated_delay = self.estimate_delay_at_boarding_station()
        if estimated_delay > 0:
            return "%sm late" % (estimated_delay,)
        elif estimated_delay < 0:
            return "%sm early" % (abs(estimated_delay),)
        else:
            return "on-time"

    def short_summary(self):
        if not (self.is_current() and self.arrives_in_departure_window()):
            s = ""
        else:
            s = "%s from %s (%s). Currently at %s." % \
                (self.start_time_str,
                self.start_loc_str,
                self.delay_description(),
                self.location)
            if self.alert:
                s += " Alert: %s" % (self.alert,)
        return s

    def full_summary(self):
        s = ""
        if not self.arrives_in_departure_window():
            s += "[Out Of Schedule] "
        if not self.is_current():
            s += "[In the past] "

        s += "Trip %s. %s from %s (%s). Currently at %s. Alert: %s" % \
            (self.trip_id,
             self.start_time_str,
             self.start_loc_str,
             self.delay_description(),
             self.location,
             self.alert)
        return s


def extract_trip(j, trip_id):
    t = Trip(trip_id)
    delay_data = filter(lambda x: x["tripId"] == trip_id, j["delays"])
    #transposition_data = filter(
    #    lambda x: x["tripId"] == trip_id, j["transpositions"])
    vehicle_data = filter(lambda x: x["tripId"] == trip_id, j["vehicles"])
    alert_data = filter(lambda x: x["tripId"] == trip_id, j["alerts"])

    if delay_data:
        t.start_time_str = delay_data[0]["start"]
        # "hh:mm" to timedelta
        t.start_time_timedelta = timedelta(
            0, 0, 0, 0, *map(int, reversed(delay_data[0]["start"].split(":"))))
        t.start_loc_int = int(delay_data[0]["stopId"])
        t.start_loc_str = conf.stop_ids.get(
            t.start_loc_int, "Unknown")
        # offsets is a string of comma sep list of alternating times and delays
        # e.g. "14:15,16,17:10,14,17:42,13,18:25,11,19:57,10,20:20,9"
        # Convert to list of tuples of datetime.timedelta & delay as int
        #
        # Sometimes offsets is not present in the delay data
        if "offsets" in delay_data[0]:
            offsets_raw_list = delay_data[0]["offsets"].split(",")
        else:
            offsets_raw_list = []
        t.offset_tuples = zip(
            [timedelta(0, 0, 0, 0, *map(int, reversed(x.split(":"))))
             for x in (itertools.islice(offsets_raw_list, 0, None, 2))],
            map(int, itertools.islice(offsets_raw_list, 1, None, 2))
        )

    if vehicle_data:
        t.location = vehicle_data[0]["lp"].rsplit(":", 2)[0]
    if alert_data:
        t.alert = alert_data[0]["title"]

    t.populate_estimated_arrival_times()
    return t


if __name__ == "__main__":
    r = requests.get(BASE_URL % (conf.ROUTES,))
    j = r.json()

    print "Retrieved at: %s" % \
          (datetime.fromtimestamp(j["timestamp"]).ctime(),)

    # Save the realtime data for troubleshooting and verification
    with open("/Users/esteele/realtime.json", "w") as f:
        f.write(r.text)

    # Trains only appear in the vehicles list once they have actually departed.
    # Trains that are past their departure time ("start") but have not left their
    #  origin are not listed in vehicles until they've actually left the station.
    trips = []
    for tripId in [v["tripId"] for v in j["vehicles"] if v["route"] == conf.ROUTES]:
        trips.append(extract_trip(j, tripId))

    print "------"
    for t in trips:
        if t.is_current() and t.arrives_in_departure_window():
            print t.short_summary()
    print "------"
    for t in trips:
        print t.full_summary()
