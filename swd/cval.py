
from validation_wrapper import wrap_old_validation_as_new as validate

class Collocation:
    def __init__(self, colo_name):
        self.name = colo_name

    def get_name(self):
        return self.name

    def get_path(self):
        return "/home/edwste/ProdCentralizedRepo"


@validate
def validate(path, colo):
    print "Calling old style validate with path %s and colo %s" % (path, colo)


if __name__ == "__main__":
    c = Collocation("mgi")
    #validate("onearg", "twoarg")
    validate(c)
