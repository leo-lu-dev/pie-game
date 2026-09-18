import unittest

import httpx

from data_pipeline.agents.critic import AgentCriticError
from data_pipeline.agents.gemini import GeminiCriticTransport


class GeminiTransportTests(unittest.TestCase):
    def test_returns_text_from_generate_content_response(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers['x-goog-api-key'], 'test-key')
            payload = request.read()
            self.assertIn(b'"responseMimeType":"application/json"', payload)
            self.assertIn(b'"responseJsonSchema"', payload)
            return httpx.Response(
                200,
                json={'candidates': [{'content': {'parts': [{'text': '{"verdict":"review"}'}]}}]},
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with GeminiCriticTransport('test-key', client=client) as transport:
            self.assertEqual(transport.complete(system_prompt='system', user_prompt='user'), '{"verdict":"review"}')
        client.close()

    def test_wraps_api_errors_without_exposing_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text='invalid key', request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with GeminiCriticTransport('secret-key', client=client) as transport:
            with self.assertRaises(AgentCriticError):
                transport.complete(system_prompt='system', user_prompt='user')
        client.close()


if __name__ == '__main__':
    unittest.main()
