import os
import subprocess
import math
from pprint import pprint

import yaml
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


class NotFound(Exception):
    pass


def _parse_conf(path):
    try:
        with open(path) as conf_file:
            conf = yaml.safe_load(conf_file)
            default_data_file = (
                conf["default_data_file"]
                if "default_data_file" in conf.keys()
                else None
            )
            suites = (
                conf["benchmark_suites"] if "benchmark_suites" in conf.keys() else None
            )
            executors = (
                conf["executors"] if "executors" in conf.keys() else None
            )

            experiments = (
                conf["experiments"] if "experiments" in conf.keys() else None
            )
    except IOError:
        raise NotFound("cannot open %s" % path)

    executables = {}

    for exec_key in executors:
        executable = executors[exec_key]['path'] + "/" + executors[exec_key]['executable']
        executables[exec_key] = executable

    if not default_data_file:
        raise NotFound("no default_data_file")

    if not suites:
        raise NotFound("no benchmark_suites")

    return {"default_data_file": default_data_file,  "experiments": experiments,
            "suites": suites, "executables": executables}


def _parse_cpu_brand(brand):
    if "AMD" in brand:
        return "AMD"
    elif "Intel" in brand:
        return "Intel"
    else:
        return "Unknown"


def _print_header():
    print("execution\tbenchmark\titerations\tinvocations\telapsed time (ms)")


def _fill_blank_command(command, variable, value):
    for i, c in enumerate(command):
        if variable in c:
            new_c = c.replace(variable, str(value))
            command[i] = new_c
    return command


def execute_suites(configuration):
    default_data_file = configuration["default_data_file"]
    experiments = configuration["experiments"]
    suites = configuration["suites"]
    executables = configuration["executables"]

    _print_header()

    for exp_name in experiments:
        executions = experiments[exp_name]["executions"]
        for execution in executions:
            for exec_name in execution:
                exec_suites = execution[exec_name]['suites']
                executable = executables[exec_name]
                for exec_suite in exec_suites:
                    suite = suites[exec_suite]
                    benchmarks = suite['benchmarks']
                    cmdline = suite['command'].split()
                    iterations = suite['iterations']
                    invocations = suite['invocations']
                    cmdline = _fill_blank_command(cmdline, "%(iterations)s", iterations)

                    commands = []
                    if 'variable_values' in suite:
                        variable_values = suite['variable_values']
                    else:
                         commands.append([executable] + cmdline)

                    for benchmark in benchmarks:
                        benchmark_name = next(iter(benchmark))
                        extra_args = benchmark[benchmark_name]['extra_args'] \
                            if 'extra_args' in benchmark[benchmark_name] else None
                        variable_values = benchmark['variable_values'] \
                            if 'variable_values' in benchmark else None

                        for cmdline in commands:
                            cmdline = _fill_blank_command(cmdline, "%(benchmark)s", benchmark_name)
                            cmdline = cmdline + [str(extra_args)]
                            output = subprocess.check_output(cmdline)
                            results = output.splitlines()
                            for l in results:
                                print(l)


def reset():
    _reset_shielding()


def main():
    cpuinfo = get_cpu_info()
    arch = cpuinfo["arch"]
    brand = _parse_cpu_brand(cpuinfo["brand_raw"])
    num_core = int(cpuinfo["count"])

    result = activate_shielding(num_core)
    if result == "failed":
        print("setting cpu shielding is failed.")

    result = _set_no_turbo(with_no_turbo=True, brand=brand)
    if result == "failed":
        print("disabling turbo boost is failed.")

    reset()


if __name__ == "__main__":
    # main()
    conf = _parse_conf("test.conf")
    execute_suites(conf)
