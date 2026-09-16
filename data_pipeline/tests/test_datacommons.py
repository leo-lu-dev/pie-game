import unittest

import httpx

from data_pipeline.sources.datacommons import DataCommonsAdapter, DataCommonsError


def response_for(request: httpx.Request) -> httpx.Response:
    payload = {
        "byVariable": {
            f"var-{index}": {
                "byEntity": {
                    "country/CAN": {
                        "orderedFacets": [{"facetId": "facet-1", "observations": [{"date": "2024", "value": index * 10}]}]
                    }
                }
            }
            for index in range(1, 6)
        },
        "facets": {"facet-1": {"importName": "Example Census", "provenanceUrl": "https://example.test/source"}},
    }
    return httpx.Response(200, json=payload, request=request)


class DataCommonsAdapterTests(unittest.TestCase):
    def adapter(self, client: httpx.Client) -> DataCommonsAdapter:
        return DataCommonsAdapter(
            entity_dcid="country/CAN",
            variables={f"category-{index}": f"var-{index}" for index in range(1, 6)},
            dataset_id="example-census",
            measure="count",
            geography="Canada",
            client=client,
        )

    def test_fetch_preserves_values_and_facet_provenance(self):
        client = httpx.Client(transport=httpx.MockTransport(response_for))
        with self.adapter(client) as adapter:
            dataset = adapter.fetch()
        self.assertEqual([value.value for value in dataset.values], [10, 20, 30, 40, 50])
        self.assertEqual(dataset.facet_id, "facet-1")
        self.assertEqual(dataset.source_url, "https://example.test/source")
        self.assertEqual(dataset.source_metadata["variables"]["category-1"], "var-1")

    def test_rejects_mixed_facets(self):
        def mixed_response(request: httpx.Request) -> httpx.Response:
            payload = response_for(request).json()
            payload["byVariable"]["var-5"]["byEntity"]["country/CAN"]["orderedFacets"][0]["facetId"] = "facet-2"
            return httpx.Response(200, json=payload, request=request)

        client = httpx.Client(transport=httpx.MockTransport(mixed_response))
        with self.assertRaises(DataCommonsError):
            self.adapter(client).fetch()


if __name__ == "__main__":
    unittest.main()

