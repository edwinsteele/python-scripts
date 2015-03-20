

def wrap_old_validation_as_new(func):
    def inner(*args, **kwargs): #1
        print "Arguments were: %s, %s" % (args, kwargs)
        path = args[0].get_path()
        colo = args[0].get_name()
        return func(path, colo)
    return inner
