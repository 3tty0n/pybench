import os
import subprocess
import math
from pprint import pprint

from cpuinfo import get_cpu_info


def _shield_num_core_bounds(num_core):
    lower = int(math.floor(math.log(num_core)))
    upper = num_core - 1
    return lower, upper


def _activate_shielding(num_core):
    lower, upper = _shield_num_core_bounds(num_core)
    shielded_core = "%d-%d" % (lower, upper)
    cmdline = ["cset", "shield", "-c", shielded_core]
    try:
        output = subprocess.check_output(cmdline, stderr=subprocess.STDOUT)

    except (subprocess.CalledProcessError, OSError):
        return "failed"


def _reset_shielding():
    cmdline = ["cset", "shield", "-r"]
    try:
        output = subprocess.check_output(cmdline, stderr=subprocess.STDOUT)

    except (subprocess.CalledProcessError, OSError):
        return "failed"



def _set_no_turbo(with_no_turbo, brand):
    is_intel = True if brand == 'Intel' else False
    is_amd = True if brand == 'AMD' else False
    try:
        if is_intel:
            value = "1"
            with open("/sys/devices/system/cpu/intel_pstate/no_turbo", "w") as nt_file:
                nt_file.write(value + "\n")
            return with_no_turbo
        elif is_amd:
            value = "0"
            with open("/sys/devices/system/cpu/cpufreq/boost", "w") as nt_file:
                nt_file.write(value + "\n")
            return with_no_turbo
        else:
            return "failed"
    except IOError:
        return "failed"



def _parse_cpu_brand(brand):
    if 'AMD' in brand:
        return 'AMD'
    elif 'Intel' in brand:
        return 'Intel'
    else:
        return 'Unknown'


def reset():
    _reset_shielding()


def main():
    cpuinfo = get_cpu_info()
    arch = cpuinfo['arch']
    brand = _parse_cpu_brand(cpuinfo['brand_raw'])
    num_core = int(cpuinfo['count'])

    result = activate_shielding(num_core)
    if result == "failed":
        print("setting cpu shielding is failed.")

    # result = _set_no_turbo(with_no_turbo=True, brand=brand)
    # if result == "failed":
    #     print("disabling turbo boost is failed.")

    reset()


if __name__ == "__main__":
    main()
