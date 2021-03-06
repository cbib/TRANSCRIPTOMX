#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Credits: Claire Lescoat, Macha Nikolski


"""
Remove proteins with number of NA above specified threshold
"""

import argparse
import logging.config
import os
import pandas as pd
import helpers as h
import paths
import functions_quality_check as fqc


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", "-i", help='Input file (csv)')
    parser.add_argument("--output_file_complete", "-oc", help='File (csv) with additional column with % nan values per '
                                                              'protein and group')
    parser.add_argument("--output_file_filtered", "-of", help='File (csv) with only included proteins')
    parser.add_argument("--file_id", "-f", help='Unique ID')

    args = parser.parse_args()
    return args


def get_groups(data_structure, values_cols_prefix):
    """
    Returns list of strings that describe the beginning of values column to select.
        Example: ['VAL_Patient', 'VAL_Control']
    # TODO : move to helpers.py
    """

    # +1 for all data columns prefix (ex: 'VAL')
    depth = len(rule_params['clean_na']['on']) + 1
    list_group_prefix = h.dict_to_list(data_structure, depth, values_cols_prefix, [])

    return list_group_prefix


if __name__ == "__main__":
    args = get_args()
    rule_params = h.load_json_parameter(args.file_id)
    filename = h.filename(args.input_file)
    data_structure = h.load_json_data(args.file_id, filename, rule_params['all']['divide'])

    logpath = os.path.join(paths.global_data_dir, args.file_id, 'log/remove_lines_na.log')
    logger = h.get_logger(logpath)

    data_df = pd.read_csv(args.input_file, header=0, index_col=None)
    values_cols_prefix = rule_params['all']['values_cols_prefix']

    # NaN per protein and per group
    group_prefix = get_groups(data_structure, values_cols_prefix)

    result_df, stats_per_groups = fqc.na_per_group(data_df,
                                                  group_prefix,
                                                  values_cols_prefix)

    result_df = fqc.flag_row_supp(result_df, stats_per_groups, rule_params['clean_na']['max_na_percent_proteins'], 'na')

    if rule_params['clean_na']['keep_specific']:
        result_df = fqc.keep_specific_proteins_na(result_df, 'nan_percentage', 'na')

    # NaN per samples
    stats_per_sample = fqc.na_per_samples(data_df, values_cols_prefix, rule_params["clean_na"]["max_na_percent_samples"])

    # create json with information on % of NaN for samples
    out = os.path.join(paths.global_data_dir, args.file_id, 'no_na', 'samples_{}.json'.format(filename))
    fqc.export_json_sample(stats_per_sample, out, values_cols_prefix)

    # filter dataframe for following analysis
    # remove row to discard
    filtered_df = fqc.remove_flagged_rows(result_df, 'exclude_na', 1)
    # remove samples to discard AND keep only base df (as defined in the config file) and abundances values columns
    filtered_df = fqc.remove_flagged_samples(filtered_df, stats_per_sample['to_exclude'], rule_params)

    # Export dataframe with only proteins/samples compliant with threshold
    h.export_result_to_csv(filtered_df, args.output_file_filtered)

    # Export dataframe with all data and information on nan percentage per group and protein
    h.export_result_to_csv(result_df, args.output_file_complete)

    logging.info("Keeping " + str(len(filtered_df)) + " proteins with current parameters.")
    logging.info("Keeping " + str(len(stats_per_sample[stats_per_sample['to_exclude'] == False])) +
                 " samples with current parameters.")