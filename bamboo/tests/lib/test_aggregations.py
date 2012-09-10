from collections import defaultdict
import pickle

import numpy as np

from lib.constants import SCHEMA
from models.dataset import Dataset
from models.observation import Observation
from test_calculator import TestCalculator


class TestAggregations(TestCalculator):

    AGGREGATION_RESULTS = {
        'amount': 2007.5,
        'gps_latitude': 624.089497667,
    }

    GROUP_TO_RESULTS = {
        ('food_type', ):
            pickle.load(
                open('tests/fixtures/good_eats_agg_group_food_type.p', 'rb')),
        ('food_type', 'rating'):
            pickle.load(
                open('tests/fixtures/good_eats_agg_group_food_type_rating.p', 'rb')),
    }

    def setUp(self):
        TestCalculator.setUp(self)
        self.calculations_to_columns = {
            'sum(amount)': 'amount',
            'sum(gps_latitude)': 'gps_latitude',
        }
        self.calculations = self.calculations_to_columns.keys()
        self.expected_length = defaultdict(int)

    def _calculations_to_results(self, formula, row):
        name = self.calculations_to_columns[formula]
        if self.group:
            groups = tuple(self.group)
            res = self.GROUP_TO_RESULTS[groups][name]
            column = row[self.group[0]] if len(self.group) <= 1 else tuple([row[group] for group in self.group])
            res = res[column]
            return res
        else:
            return self.AGGREGATION_RESULTS[name]

    def _test_calculation_results(self, name, formula):
        if self.group:
            if not isinstance(self.group, list):
                self.group = [self.group]
            self.group_key = str(self.group)
        else:
            self.group_key = ''

        linked_dataset_id = self.dataset.linked_datasets[self.group_key]

        if self.group_key not in self.expected_length and self.group is not None:
            self.expected_length[self.group_key] = len(self.group)

        # add an extra column for the group names
        self.expected_length[self.group_key] += 1

        # retrieve linked dataset
        self.assertFalse(linked_dataset_id is None)
        linked_dataset = Dataset.find_one(linked_dataset_id)
        linked_dframe = Observation.find(linked_dataset, as_df=True)

        column_labels_to_slugs = linked_dataset.build_labels_to_slugs()
        name = column_labels_to_slugs[name]

        self.assertTrue(name in linked_dframe.columns)

        self.assertEqual(len(linked_dframe.columns),
                         self.expected_length[self.group_key])

        # test that the schema is up to date
        self.assertTrue(SCHEMA in linked_dataset.record.keys())
        self.assertTrue(isinstance(linked_dataset.data_schema, dict))
        schema = linked_dataset.data_schema

        # test slugified column names
        column_names = [name]
        if self.group:
            column_names.extend(self.group)
        for column_name in column_names:
            self.assertTrue(column_name in schema.keys())

        for idx, row in linked_dframe.iterrows():
            result = np.float64(row[name])
            stored = self._calculations_to_results(formula, row)
            # np.nan != np.nan, continue if we have two nan values
            if np.isnan(result) and np.isnan(stored):
                continue
            msg = self._equal_msg(result, stored, formula)
            self.assertAlmostEqual(result, stored, self.places, msg)

    def test_calculator_with_delay(self):
        self._test_calculator()

    def test_calculator_without_delay(self):
        self._test_calculator(delay=False)

    def test_calculator_with_group(self):
        self.group = 'food_type'
        self._test_calculator(delay=False)

    def test_calculator_with_group_list(self):
        self.group = ['food_type']
        self._test_calculator(delay=False)

    def test_calculator_with_multigroup_list(self):
        self.group = ['food_type', 'rating']
        self._test_calculator(delay=False)
