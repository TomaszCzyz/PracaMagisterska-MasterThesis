import logging
import multiprocessing as mp
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import json

# These Examples are only seemingly unused.
# They are instantiate by globals() function for all classes with name like 'Example*'
from Examples import Example1, Example2, Example3, Example4
from Utilis import worst_case_error_n
from alg2014.Alg2014_implementation import AlgKP
from alg2014.Alg2014_implementation_high_prec import AlgKPmp
from alg2015.Alg2015_implementation import AlgMP


def apply_global_plot_styles():
    plt.rcParams['axes.linewidth'] = 0.1
    plt.rcParams['font.size'] = 7
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["figure.figsize"] = [6.4, 4.8 * 0.8]
    plt.rcParams['figure.dpi'] = 175
    plt.rcParams['savefig.dpi'] = 175


class ResultsCollector:
    """
    This class collect results using method callback_handler.
    Passed data should be tuple (error, alg_m, alg_noise), where
        error - error of approximation
        alg_m - initial mesh resolution associated with the error
        alg_noise - noise associated with the error

    Additionally, prints available results when 'print_threshold'(percent of finished tasks) is achieved.
    If plot_threshold > 100, then no results are printed.
    """

    def __init__(self, max_count, data, plot_threshold=None, save_results=False):
        self.data = data
        self.tasks_number = max_count
        self.plot_threshold = plot_threshold if plot_threshold is not None else 101
        self.save_results = save_results

        self.example_function = create_example(data['example_fun_name'])
        self.finished_tasks = 0
        self.log10_errors_for_noise = {}
        self.log10_m_for_noise = {}
        self.path = 'data/{}/{}/r_{}/p_{}/'.format(
            self.data['algorithm_name'],
            self.data['example_fun_name'],
            self.data['f__r'],
            self.data['p'])
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def callback_handler(self, args):
        """
        Stores new data about the error in two dictionaries:
        {noise: [-log10(error1), -log10(error4), ..., -log10(error2)]} and
        {noise: [log10(m), log10(m), ..., log10(m)]},
        where m is number of knots in initial mesh of algorithm.
        Note that in case of parallel computations we obtain results in arbitrary order
        and data about 'm' and 'noise' is required to keep track of calculated errors.

        Additionally, prints available results when
        'print_threshold'(percent of finished tasks) is achieved.
        """
        error, alg_m, alg_noise = args
        self.finished_tasks += 1
        self.print_status(args)

        if alg_noise not in self.log10_errors_for_noise.keys():
            self.log10_errors_for_noise[alg_noise] = []
            self.log10_m_for_noise[alg_noise] = []

        self.log10_errors_for_noise[alg_noise].append(-np.log10(error))
        self.log10_m_for_noise[alg_noise].append(np.log10(alg_m))

        if self.finished_tasks / self.tasks_number >= (self.plot_threshold / 100):
            self.plot_results()

        if self.finished_tasks == self.tasks_number and self.save_results:
            self.save_results_to_file()

    def plot_results(self, save=False):
        """
        Plots results stored in: self.log10_errors_for_noise and self.log10_m_for_noise.
        It also saves plot, if save=True, see save_plot() method.
        """
        fig, ax = plt.subplots()

        sorted_noises = sorted(self.log10_m_for_noise.keys(), key=lambda x: (x is not None, x), reverse=False)
        ref_noise = sorted_noises[0]  # we need a noise to reference data in dictionaries

        x_values = self.log10_m_for_noise[ref_noise]
        x_min, x_max = min(x_values), max(x_values)

        # data for plot of the theoretical error
        theoretical_error_exponent = -(self.data['f__r'] + 1)
        m_original = np.array(np.floor(np.power(10, x_values)), dtype='float64')
        theoretical_error = np.power(m_original, theoretical_error_exponent)
        reference_line = -np.log10(theoretical_error)

        markers = ['1', '2', '1', '2']
        colors = ['orange', 'grey', 'green', 'blue']
        supscript = str.maketrans("0123456789-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁼⁽⁾")
        subplot_nr = 0
        for key_noise in sorted_noises:
            plt.plot(
                sorted(self.log10_m_for_noise[key_noise]), sorted(self.log10_errors_for_noise[key_noise]),
                c=colors[subplot_nr],
                marker=markers[subplot_nr],
                linewidth=1,
                label=r'$\delta$=' + ("{:.0e}".format(key_noise) if key_noise is not None else '0'),
                alpha=0.5
            )
            subplot_nr += 1

        plt.plot(
            sorted(x_values)[:int(len(x_values) * 0.7)], sorted(reference_line)[:int(len(reference_line) * 0.7)],
            color='grey',
            linestyle='--',
            linewidth=1,
            label=("m{}".format(theoretical_error_exponent)).translate(supscript)
        )

        # description and general plot styles
        base = 0.5
        plt.xlim([x_min - 0.1, x_max + 0.1])
        plt.xticks(np.arange(base * round(x_min / base), base * round(x_max / base) + base, base))
        ax.xaxis.set_tick_params(width=0.5, color='grey')
        ax.yaxis.set_tick_params(width=0.5, color='grey')
        fig.text(0.5, 0.008, r'$\log_{10}m$', ha='center')
        fig.text(0.001, 0.5, r'$-\log_{10}err$', va='center', rotation='vertical')
        plt.grid(linewidth=0.5, linestyle=':')
        plt.legend(numpoints=1)
        plt.tight_layout()

        plt.suptitle("{} for {}(r={}, p={})\nbased on {} sample functions ({})".format(
            self.data['algorithm_name'], self.data['example_fun_name'],
            self.data['f__r'],
            self.data['p'],
            self.data['executions_number'],
            datetime.now()))

        if save:
            self.save_plot()
        plt.show()

    def save_plot(self):
        """
        Saves plot to: './<self.path>/plot_<nr_of_evaluations>evaluations_<nr>.jpg',
        where <nr> is first loose number determined by current content of folder
        """
        plot_nr = 0
        while os.path.exists("{}plot_{}evaluation_{}.jpg".format(self.path, self.data['executions_number'], plot_nr)):
            plot_nr += 1

        plt.savefig("{}plot_{}evaluation_{}.jpg".format(self.path, self.data['executions_number'], plot_nr))

    def print_status(self, args=None):
        """
        Prints progress of calculations
        """
        if args:
            print("finished task for m={} and noise={}".format(args[1], args[2]))
        print("finished tasks: {}/{}".format(self.finished_tasks, self.tasks_number), end='\r')

    def save_results_to_file(self):
        with open(self.path + "error_results.txt", "a+") as file:
            file.write("Data from run of {}\n".format(self.data))
            file.write("log10_m_for_noise dict: {}\n)".format(json.dumps(self.log10_m_for_noise)))
            file.write("log10_errors_for_noise dict: {}\n)".format(json.dumps(self.log10_errors_for_noise)))


def create_example(example_name, delta=None, f__r=4):
    """
    Creates Example* function instance with specified noise and function regularity.
    The purpose of this method is to allow parallel computation for the same function with different noise.
    """
    name = example_name.capitalize()
    if name[:7].lower() == 'example':
        return globals()[name](delta, f__r)

    raise Exception("incorrect example function name")


def create_algorithm(algorithm_name, example_function, knots_number, p=2):
    """
    Create instance of algorithm with specified data.
    """
    if algorithm_name.lower() == 'AlgKP'.lower():
        return AlgKP(example_function, knots_number)
    if algorithm_name.lower() == 'AlgKPmp'.lower():
        return AlgKPmp(example_function, knots_number)
    if algorithm_name.lower() == 'AlgMP'.lower():
        return AlgMP(example_function, knots_number, p)

    raise Exception("incorrect algorithm name")


def calculate(repeat_count, knots_counts, deltas, algorithm_name, example_fun_name, p, parallel=False, f__r=4):
    """
    Calculates approximation error for specified algorithm and function with respect to norm L_p (1 <= p <= infinity)
    Calculations are repeated 'n_times' for each knots count from 'array'.
    This method returns 'ResultCollector' class, which stores all collected results.

    For infinity norm pass the string p='infinity'.
    If you want to override regularity of function use 'f__r' parameter.
    Set parallel=True for parallel computation
    """
    extra_data = {
        'algorithm_name': algorithm_name,
        'example_fun_name': example_fun_name,
        'executions_number': repeat_count,
        'f__r': f__r,
        'p': p
    }
    tasks_number = len(knots_counts) * len(deltas)
    results_collector = ResultsCollector(tasks_number, extra_data, plot_threshold=None, save_results=True)

    if parallel:
        with mp.Pool(processes=mp.cpu_count() - 2) as pool:
            apply_results = []
            for knots_number in reversed(knots_counts):
                for noise in deltas:
                    print("starting processing algorithm({} times) for m={} and delta={}..."
                          .format(repeat_count, knots_number, noise))

                    function = create_example(example_fun_name, noise, f__r=f__r)
                    alg = create_algorithm(algorithm_name, function, knots_number, p)

                    apply_result = pool.apply_async(
                        func=worst_case_error_n,
                        # args=(alg, 1 if noise is None else repeat_count, p),  # for NOT random singularity
                        args=(alg, repeat_count, p),
                        callback=results_collector.callback_handler)

                    apply_results.append(apply_result)

            results_collector.print_status()
            for r in apply_results:
                r.wait()

    else:
        for knots_number in reversed(knots_counts):
            for noise in deltas:
                print("running algorithm({} times) for m={}, noise={}".format(repeat_count, knots_number, noise))

                function = create_example(example_fun_name, noise, f__r=f__r)
                alg = create_algorithm(algorithm_name, function, knots_number)

                result_tuple = worst_case_error_n(
                    alg=alg,
                    # repeat_count=1 if noise is None else repeat_count,  # for NOT random singularity
                    repeat_count=repeat_count,
                    lp_norm=p
                )
                results_collector.callback_handler(result_tuple)

    return results_collector


def main():
    apply_global_plot_styles()
    logging.basicConfig(level=logging.INFO, filename='Calculate.log', format="%(asctime)s:%(message)s")
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # input data for calculations
    m_array = [int(10 ** log10_m) for log10_m in np.linspace(1.0, 3.0, num=30)]  # 10 ** 4.7 =~ 50118;
    noises = [None, 1e-9, 1e-6, 1e-3]
    repeat_count = 500
    alg = 'algKPmp'  # 'algKPmp' 'algKP' 'algMP'
    example = 'Example1'
    p_norm = 'infinity'
    r = 4

    create_example(example).plot()

    start_time = datetime.now()
    logging.info('Started at {}'.format(start_time.strftime("%d/%m/%Y %H:%M:%S")))

    results_collector = calculate(repeat_count, m_array, noises, alg, example, p=p_norm, parallel=True, f__r=r)
    results_collector.plot_results(save=True)

    end_time = datetime.now()
    processing_time = end_time - start_time

    logging.info('Finished at {} (execution time: {})'.format(
        end_time.strftime("%d/%m/%Y %H:%M:%S"), str(processing_time)))

    return results_collector


if __name__ == '__main__':
    results = main()
