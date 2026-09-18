import unittest

import httpx

from data_pipeline.sources.eurostat import EurostatAdapter, EurostatError
from data_pipeline.sources.owid import OwidAdapter


class ExternalSourceAdapterTests(unittest.TestCase):
    def test_owid_normalizes_latest_entity_row_and_metadata(self):
        csv_text = (
            "Entity,Code,Year,Alpha,Beta,Gamma,Delta,Epsilon\n"
            "World,OWID_WRL,2022,1,2,3,4,5\n"
            "World,OWID_WRL,2023,10,20,30,40,50\n"
            "Canada,CAN,2023,99,99,99,99,99\n"
        )
        metadata = {
            "chart": {"title": "Example composition", "originalChartUrl": "https://example.test/chart"},
            "columns": {
                column: {"titleShort": column, "unit": "%"}
                for column in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon")
            },
        }

        def response(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith(".csv"):
                return httpx.Response(200, text=csv_text, request=request)
            return httpx.Response(200, json=metadata, request=request)

        client = httpx.Client(transport=httpx.MockTransport(response))
        with OwidAdapter(slug="example", client=client) as adapter:
            dataset = adapter.fetch()
        self.assertEqual(dataset.time_period, "2023")
        self.assertEqual([value.value for value in dataset.values], [10, 20, 30, 40, 50])
        self.assertEqual(dataset.source_url, "https://example.test/chart")
        self.assertEqual(dataset.unit, "%")

    def test_eurostat_reads_json_stat_dimension_and_filters_overlapping_category(self):
        payload = {
            "id": ["freq", "age", "geo"],
            "size": [1, 6, 1],
            "dimension": {
                "freq": {"category": {"index": {"A": 0}, "label": {"A": "Annual"}}},
                "age": {
                    "category": {
                        "index": {"TOTAL": 0, "Y_LT5": 1, "Y5-9": 2, "Y10-14": 3, "Y15-19": 4, "Y_GE20": 5},
                        "label": {
                            "TOTAL": "Total",
                            "Y_LT5": "Less than 5 years",
                            "Y5-9": "From 5 to 9 years",
                            "Y10-14": "From 10 to 14 years",
                            "Y15-19": "From 15 to 19 years",
                            "Y_GE20": "20 years or over",
                        },
                    }
                },
                "geo": {"category": {"index": {"EU27_2020": 0}, "label": {"EU27_2020": "European Union"}}},
            },
            "value": [999, 10, 20, 30, 40, 100],
        }

        def response(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload, request=request)

        client = httpx.Client(transport=httpx.MockTransport(response))
        with EurostatAdapter(
            dataset_code="example",
            category_dimension="age",
            filters={"geo": "EU27_2020"},
            exclude_category_ids={"TOTAL"},
            client=client,
        ) as adapter:
            dataset = adapter.fetch()
        self.assertEqual([value.category_id for value in dataset.values], ["Y_LT5", "Y5-9", "Y10-14", "Y15-19", "Y_GE20"])
        self.assertEqual([value.value for value in dataset.values], [10, 20, 30, 40, 100])

    def test_eurostat_requires_non_category_dimensions_to_be_filtered(self):
        payload = {
            "id": ["freq", "age"],
            "size": [2, 5],
            "dimension": {
                "freq": {"category": {"index": {"A": 0, "M": 1}, "label": {"A": "Annual", "M": "Monthly"}}},
                "age": {"category": {"index": {str(index): index for index in range(5)}, "label": {str(index): str(index) for index in range(5)}}},
            },
            "value": list(range(10)),
        }

        def response(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload, request=request)

        with EurostatAdapter(
            dataset_code="example",
            category_dimension="age",
            client=httpx.Client(transport=httpx.MockTransport(response)),
        ) as adapter:
            with self.assertRaisesRegex(EurostatError, "must reduce dimension freq"):
                adapter.fetch()


if __name__ == "__main__":
    unittest.main()
