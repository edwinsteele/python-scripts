import datetime
import requests

CEN_TO_BLX_ROUTE = "CR_bm_d"
BLX_TO_CEN_ROUTE = "CR_bm_u"

# 5am  (should fall neatly between the 4:39am and 5:24am)
FIRST_DEPARTURE_TIME = datetime.timedelta(hours=5)
# Will catch the 6:24am but not the 6:40am)
LAST_DEPARTURE_TIME = datetime.timedelta(hours=6, minutes=35)

# LIT-BLX 91-104 minutes
LIT_TO_BLX_DURATION_MIN = datetime.timedelta(hours=1, minutes=31)
LIT_TO_BLX_DURATION_MAX = datetime.timedelta(hours=1, minutes=44)
# MOU-BLX 63-72 minutes
MOU_TO_BLX_DURATION_MIN = datetime.timedelta(hours=1, minutes=3)
MOU_TO_BLX_DURATION_MAX = datetime.timedelta(hours=1, minutes=12)
# KAT-BLX 44-51 minutes
KAT_TO_BLX_DURATION_MIN = datetime.timedelta(minutes=44)
KAT_TO_BLX_DURATION_MAX = datetime.timedelta(minutes=51)

stop_ids = {
    278651: "Mount Victoria",
    2790141: "Lithgow",  # Platform 1
    2790142: "Lithgow",  # Platform 2
    2780201: "Katoomba",
    -1: "Unknown",
}

BASE_URL = "http://realtime.grofsoft.com/tripview/realtime?routes=%s&type=dtva"
DIRECTION = BLX_TO_CEN_ROUTE

r = requests.get(BASE_URL % (DIRECTION,))
j = r.json()

print "Retrieved at: %s" % \
      (datetime.datetime.fromtimestamp(j["timestamp"]).ctime(),)


def get_estimated_arrival_times(trip_data):
    start_time = trip_data["start_time_timedelta"]
    if trip_data["start_loc_str"] == "Lithgow":
        est_arrival_earliest = start_time + LIT_TO_BLX_DURATION_MIN
        est_arrival_latest = start_time + LIT_TO_BLX_DURATION_MAX
    elif trip_data["start_loc_str"] == "Mount Victoria":
        est_arrival_earliest = start_time + MOU_TO_BLX_DURATION_MIN
        est_arrival_latest = start_time + MOU_TO_BLX_DURATION_MAX
    elif trip_data["start_loc_str"] == "Katoomba":
        est_arrival_earliest = start_time + KAT_TO_BLX_DURATION_MIN
        est_arrival_latest = start_time + KAT_TO_BLX_DURATION_MAX
    else:
        # No chance of being in schedule
        est_arrival_earliest = datetime.timedelta.min
        est_arrival_latest = datetime.timedelta.max

    return est_arrival_earliest, est_arrival_latest


def train_arrives_between_first_and_last_departure_time(trip_data):
    return trip_data["est_arrival_earliest"] > FIRST_DEPARTURE_TIME and \
        trip_data["est_arrival_latest"] < LAST_DEPARTURE_TIME


def extract_trip(j, trip_id):
    delay_data = filter(lambda x: x["tripId"] == trip_id, j["delays"])
    transposition_data = filter(
        lambda x: x["tripId"] == trip_id, j["transpositions"])
    vehicle_data = filter(lambda x: x["tripId"] == trip_id, j["vehicles"])
    alert_data = filter(lambda x: x["tripId"] == trip_id, j["alerts"])
    
    if transposition_data:
        print "Trip %s has transposition data... wierd: %s" % \
              (trip_id, transposition_data)

    trip_data = {}
    if delay_data:
        trip_data["start_time_str"] = delay_data[0]["start"]
        # python datetime/time handling, why do you make me do these things?
        hours, minutes = map(int, delay_data[0]["start"].split(":"))
        trip_data["start_time_timedelta"] = \
            datetime.timedelta(hours=hours, minutes=minutes)
        trip_data["start_loc_int"] = int(delay_data[0]["stopId"])
        trip_data["start_loc_str"] = stop_ids.get(
            trip_data["start_loc_int"], "Unknown")
    else:
        trip_data["start_time_str"] = "unknown"
        # This means it'll never arrive in the window
        trip_data["start_time_timedelta"] = datetime.timedelta.max
        trip_data["start_loc_int"] = "unknown"
        trip_data["start_loc_str"] = "unknown"

    if vehicle_data:
        trip_data["location"] = vehicle_data[0]["lp"].rsplit(":", 2)[0]
    else:
        trip_data["location"] = "Unknown"
    if alert_data:
        trip_data["alert"] = alert_data[0]["title"]
    else:
        trip_data["alert"] = "None"

    trip_data["est_arrival_earliest"], trip_data["est_arrival_latest"] = \
        get_estimated_arrival_times(trip_data)
    return trip_data

# Trains only appear in the vehicles list once they have actually departed.
# Trains that are past their departure time ("start") but have not left their
#  origin are not listed in vehicles until they've actually left the station.
for tripId in [v["tripId"] for v in j["vehicles"] if v["route"] == DIRECTION]:
    t_d = extract_trip(j, tripId)
    if not train_arrives_between_first_and_last_departure_time(t_d):
        print "[Out Of Schedule] ",
    print "Trip %s from %s @ %s. Currently at %s. Alert: %s" % \
        (tripId,
         t_d["start_loc_str"],
         t_d["start_time_str"],
         t_d["location"],
         t_d["alert"])


with open("/Users/esteele/realtime.json", "w") as f:
    f.write(r.text)
