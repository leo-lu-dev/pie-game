import unittest

import httpx

from data_pipeline.agents.ollama import OllamaCriticTransport


class OllamaTransportTests(unittest.TestCase):
    def test_sends_schema_and_returns_chat_content(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, '/api/chat')
            payload = request.read()
            self.assertIn(b'"format"', payload)
            self.assertIn(b'"stream":false', payload)
            return httpx.Response(
                200,
                json={'message': {'content': '{"verdict":"review"}'}},
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with OllamaCriticTransport('http://ollama.test', 'qwen3:8b', client=client) as transport:
            self.assertEqual(transport.complete(system_prompt='system', user_prompt='user'), '{"verdict":"review"}')
        client.close()

    def test_wraps_ollama_errors(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='model not found', request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with OllamaCriticTransport(client=client) as transport:
            with self.assertRaisesRegex(RuntimeError, 'Ollama request failed with HTTP 404'):
                transport.complete(system_prompt='system', user_prompt='user')
        client.close()


if __name__ == '__main__':
    unittest.main()
