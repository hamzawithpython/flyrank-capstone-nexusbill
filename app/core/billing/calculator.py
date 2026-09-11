def calculate_cost_micros(
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    input_price_per_1m_micros: int,
    cached_input_price_per_1m_micros: int,
    output_price_per_1m_micros: int,
    reasoning_price_per_1m_micros: int,
) -> int:
    """Returns total cost in micros (millionths of a dollar), as an integer.

    Integer arithmetic throughout — no floats, per project convention.
    Sums all four token-type contributions BEFORE dividing by 1,000,000,
    not after, to avoid compounding truncation across four separate
    divisions. The final integer floor-division truncates any fractional
    micro (worth less than $0.000001) — immaterial at real volumes, but
    a deliberate, documented choice rather than an accident.
    """
    numerator = (
        input_tokens * input_price_per_1m_micros
        + cached_input_tokens * cached_input_price_per_1m_micros
        + output_tokens * output_price_per_1m_micros
        + reasoning_tokens * reasoning_price_per_1m_micros
    )
    return numerator // 1_000_000