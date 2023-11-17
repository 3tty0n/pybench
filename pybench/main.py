import os
import subprocess
import math
import re
from pprint import pprint

import yaml
from cpuinfo import get_cpu_info

from pybench.shield import _shield_num_core_bounds, _activate_shielding, _reset_shielding, _set_no_turbo


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
            executors = conf["executors"] if "executors" in conf.keys() else None

            experiments = conf["experiments"] if "experiments" in conf.keys() else None
    except IOError:
        raise NotFound("cannot open %s" % path)

    executables = {}

    for exec_key in executors:
        executable = (
            executors[exec_key]["path"] + "/" + executors[exec_key]["executable"]
        )
        executables[exec_key] = executable

    if not default_data_file:
        raise NotFound("no default_data_file")

    if not suites:
        raise NotFound("no benchmark_suites")

    return {
        "default_data_file": default_data_file,
        "experiments": experiments,
        "suites": suites,
        "executors": executors,
        "executables": executables,
    }


def _parse_cpu_brand(brand):
    if "AMD" in brand:
        return "AMD"
    elif "Intel" in brand:
        return "Intel"
    else:
        return "Unknown"


def _write_header(data_file_path):
    with open(data_file_path, "w") as f:
        f.write("invocation\titeration\tvalue\tbenchmark\texecutor\n")


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
    executors = configuration["executors"]
    executables = configuration["executables"]

    base_dir = os.getcwd()

    default_data_file_path = base_dir + "/" + default_data_file

    _write_header(default_data_file_path)

    for exp_name in experiments:
        executions = experiments[exp_name]["executions"]
        for execution in executions:
            for exec_name in execution:
                exec_suites = execution[exec_name]["suites"]
                executor = executors[exec_name]
                executor_path = executor["path"]
                executor_executable = "./" + executor["executable"]
                executor_cmdline = [executor_executable]

                executor_args = None
                if "args" in executor:
                    executor_args = executor["args"].split()
                    executor_cmdline.extend(executor_args)

                os.chdir(executor_path)

                for exec_suite in exec_suites:
                    suite = suites[exec_suite]
                    benchmarks = suite["benchmarks"]
                    iterations = suite["iterations"]
                    invocations = suite["invocations"]

                    for benchmark in benchmarks:
                        benchmark_name = next(iter(benchmark))
                        extra_args = (
                            benchmark[benchmark_name]["extra_args"]
                            if "extra_args" in benchmark[benchmark_name]
                            else None
                        )

                        commands = []

                        cmdline = suite["command"].split()
                        cmdline = _fill_blank_command(cmdline, "%(iterations)s", iterations)
                        cmdline = executor_cmdline + cmdline

                        if "variable_values" in benchmark[benchmark_name]:
                            variable_values = benchmark[benchmark_name][
                                "variable_values"
                            ]
                            for variable_value in variable_values:
                                commands.append(
                                    cmdline + [str(variable_value)]
                                )
                        elif "variable_values" in suite:
                            variable_values = benchmark[benchmark_name][
                                "variable_values"
                            ]
                            for variable_value in variable_values:
                                commands.append(
                                    cmdline + [str(variable_value)]
                                )
                        else:
                            commands.append(cmdline + cmdline)


                        for cmdline in commands:
                            cmdline = _fill_blank_command(
                                cmdline, "%(benchmark)s", benchmark_name
                            )

                            for invocation in range(1, invocations + 1):
                                output = subprocess.check_output(cmdline)
                                output_lines = output.splitlines()

                                for iteration, output_line in enumerate(output_lines):
                                    p_runtime = re.compile(b"(?<=runtime: )[0-9]+")
                                    r_runtime = p_runtime.search(output_line)
                                    if r_runtime:
                                        v_runtime = float(r_runtime.group())

                                        formatted = "{}\t{}\t{}\t{}\t{}\n".format(
                                            invocation, iteration, v_runtime, benchmark_name, exec_name
                                        )

                                        with open(default_data_file_path, "a") as data_file:
                                            data_file.write(formatted)

            os.chdir(base_dir)

def reset():
    _reset_shielding()


def main():
    cpuinfo = get_cpu_info()
    arch = cpuinfo["arch"]
    brand = _parse_cpu_brand(cpuinfo["brand_raw"])
    num_core = int(cpuinfo["count"])

    result = _activate_shielding(num_core)
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
