from runtrail.gateway.litellm_adapter import LiteLLMAdapter


def test_complete_returns_the_mocked_completion_text():
    adapter = LiteLLMAdapter("gpt-3.5-turbo")

    result = adapter.complete("say hi", mock_response="hello from mock")

    assert result == "hello from mock"


def test_complete_merges_constructor_and_call_kwargs():
    adapter = LiteLLMAdapter("gpt-3.5-turbo", temperature=0.0)

    result = adapter.complete("say hi", mock_response="ok")

    assert result == "ok"
    assert adapter.litellm_kwargs == {"temperature": 0.0}


def test_complete_routes_through_a_custom_gateway_base_url():
    # Proves "对接现有网关" — LiteLLMAdapter forwards arbitrary litellm kwargs
    # like api_base/api_key, so pointing it at a One-API-compatible proxy
    # instead of calling a provider directly needs no adapter changes.
    adapter = LiteLLMAdapter(
        "openai/gpt-3.5-turbo",
        api_base="http://one-api.example.internal/v1",
        api_key="fake-key",
    )

    result = adapter.complete("hi", mock_response="hello via one-api style gateway")

    assert result == "hello via one-api style gateway"
