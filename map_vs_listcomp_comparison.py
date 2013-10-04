import timeit
import dis
import math


def time_function_and_print(f, setup="pass"):
    cnt = 10000
    durations = timeit.repeat(f, setup, repeat=5, number=cnt)
    durations_per_loop_usec = map(lambda a: a*10**6/cnt, durations)
    name = f.__name__ if type(f) == type(timeit.repeat) else str(f)
    print("%s: Min: %.3f usec/loop. All: %s" %
          (name, min(durations_per_loop_usec),
           ", ".join(["%.3f" % (f,) for f in durations_per_loop_usec])))


def run_map():
    return set(map(str.strip, ['wat '] * 200))


def run_listcomp():
    return set([s.strip() for s in ['wat '] * 200])


def run_map_empty_list():
    return set(map(str.strip, []))


def run_listcomp_empty_list():
    return set([s.strip() for s in []])


def run_map_empty_list_with_construction():
    ['wat '] * 200
    return set(map(str.strip, []))

def run_listcomp_empty_list_with_construction():
    ['wat '] * 200
    return set([s.strip() for s in []])


def noop(s):
    return s


def noop_with_lookup(s):
    s.strip
    return s


def run_map_noop():
    return set(map(noop, ['wat '] * 200))


def run_listcomp_noop():
    return set([noop(s) for s in ['wat '] * 200])


def run_listcomp_noop_with_lookup():
    return set([noop_with_lookup(s) for s in ['wat '] * 200])


def compare():
    def time_function_and_print(f, loop_count, setup="pass",):
        durations = timeit.repeat(f, setup, repeat=5, number=loop_count)
        durations_per_loop_usec = map(lambda a: a*10**6/loop_count, durations)
        return min(durations_per_loop_usec)

    print("iterations\tloopcount\tmap\tlistcomp (us_per_iteration)")
    for i in range(1, 10000, 500):
        # Give more uniformity to run time
        loop_count = int(5000/math.sqrt(i))
        m = time_function_and_print(
            "set(map(noop, ['wat '] * {0}))".format(i),
            loop_count, setup="def noop(s): return s")
        d = time_function_and_print(
            "set([noop(s) for s in ['wat '] * {0}])".format(i),
            loop_count, setup="def noop(s): return s")
        print("{0}\t{1}\t{2:.3f}\t{3:.3f}".format(i, loop_count, m/i, d/i))


"""
if __name__ == "__main__":
    compare()
"""


if __name__ == "__main__":
    #print("run_map()")
    #dis.dis(a)
    #print("run_listcomp()")
    #dis.dis(b)
    compare()
    die
    time_function_and_print("pass")
    time_function_and_print(a)
    time_function_and_print(b)
    time_function_and_print(a_empty_list)
    time_function_and_print(b_empty_list)
    time_function_and_print(a_empty_list_with_construction)
    time_function_and_print(b_empty_list_with_construction)
    time_function_and_print(a_noop)
    time_function_and_print(b_noop)
    time_function_and_print(b_noop_with_lookup)
    time_function_and_print('set(["wat"] * 200)')
    time_function_and_print('set(wats_list)', setup='wats_list = ["wat"] * 200')
    time_function_and_print('"wat ".strip()')
    time_function_and_print('str.strip("wat ")')
    time_function_and_print('str_strip("wat ")', setup='str_strip=str.strip')
