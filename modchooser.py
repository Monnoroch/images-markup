import os
import sys


class ModChooser(object):
    def __init__(self, desc):
        self.desc = desc
        self.modes = {}

    def add(self, name, func, desc):
        self.modes[name] = (func, desc)
        return self

    def main(self, args=None):
        if args is None:
            args = sys.argv[1:]

        if args[0] == "-h" or args[0] == "--help":
            return self.print_help(sys.argv[0])

        return self.modes[args[0]][0](args[1:])

    def print_help(self, name):
        print(self.desc)
        print()
        print("Usage: " + os.path.split(name)[-1] + " [-h] mode")
        print()
        print("Available modes:\n")
        max_len = max(map(lambda x: len(x), self.modes.keys()))
        print("\n".join(map(lambda x: self._pad_to_len(x, max_len) + "\t--\t" + self.modes[x][1], self.modes.keys())))
        print()

    def _pad_to_len(self, s, ll):
        if len(s) % ll == 0:
            return s
        while len(s) % ll != 0:
            s += " "
        return s
