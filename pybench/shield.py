import subprocess
import math

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
    try:
        if brand == "Intel":
            value = str(int(with_no_turbo))
            with open("/sys/devices/system/cpu/intel_pstate/no_turbo", "w") as nt_file:
                nt_file.write(value + "\n")
            return with_no_turbo
        elif brand == "AMD":
            value = str(int(not with_no_turbo))
            with open("/sys/devices/system/cpu/cpufreq/boost", "w") as nt_file:
                nt_file.write(value + "\n")
            return with_no_turbo
        else:
            return "failed"
    except IOError:
        return "failed"
