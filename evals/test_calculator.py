from app.core.billing.calculator import calculate_cost_micros

NEXUS_1 = dict(
    input_price_per_1m_micros=3_000_000,
    cached_input_price_per_1m_micros=300_000,
    output_price_per_1m_micros=15_000_000,
    reasoning_price_per_1m_micros=15_000_000,
)


def test_input_only():
    cost = calculate_cost_micros(
        input_tokens=1000, cached_input_tokens=0, output_tokens=0, reasoning_tokens=0,
        **NEXUS_1,
    )
    assert cost == 3000  # 1000 * 3,000,000 / 1,000,000


def test_output_only():
    cost = calculate_cost_micros(
        input_tokens=0, cached_input_tokens=0, output_tokens=1000, reasoning_tokens=0,
        **NEXUS_1,
    )
    assert cost == 15000  # 1000 * 15,000,000 / 1,000,000


def test_zero_tokens():
    cost = calculate_cost_micros(
        input_tokens=0, cached_input_tokens=0, output_tokens=0, reasoning_tokens=0,
        **NEXUS_1,
    )
    assert cost == 0


def test_all_four_components():
    cost = calculate_cost_micros(
        input_tokens=1000, cached_input_tokens=500, output_tokens=200, reasoning_tokens=100,
        **NEXUS_1,
    )
    assert cost == 3000 + 150 + 3000 + 1500  # = 7650


def test_cached_input_cheaper_than_regular_input():
    regular = calculate_cost_micros(
        input_tokens=1000, cached_input_tokens=0, output_tokens=0, reasoning_tokens=0,
        **NEXUS_1,
    )
    cached = calculate_cost_micros(
        input_tokens=0, cached_input_tokens=1000, output_tokens=0, reasoning_tokens=0,
        **NEXUS_1,
    )
    assert cached < regular


def test_truncation_not_rounding():
    # 1 token at $1.50/1M = 1.5 micros scaled — must floor to 1, not round to 2.
    cost = calculate_cost_micros(
        input_tokens=1, cached_input_tokens=0, output_tokens=0, reasoning_tokens=0,
        input_price_per_1m_micros=1_500_000,
        cached_input_price_per_1m_micros=0,
        output_price_per_1m_micros=0,
        reasoning_price_per_1m_micros=0,
    )
    assert cost == 1


def test_returns_int_not_float():
    cost = calculate_cost_micros(
        input_tokens=1000, cached_input_tokens=0, output_tokens=0, reasoning_tokens=0,
        **NEXUS_1,
    )
    assert isinstance(cost, int)