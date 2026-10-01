# Cost model

The idle estimate uses only explicit event telemetry and configuration:

```text
fuel_litres = reported_idle_fuel_rate_lph × idle_seconds ÷ 3,600
idle_cost_usd = round_half_up(fuel_litres × configured_fuel_price_per_litre, 2)
potential_savings_usd = round_half_up(idle_cost_usd × configured_savings_assumption, 2)
```

Defaults are 1.50 USD/L and a 75% avoidable-cost assumption. They are sample configuration values, not a quote or actual invoice. Fuel volume is rounded to 0.001 L and currency to cents using decimal arithmetic. The calculation string is stored with each cost event. Configure `FUEL_PRICE_PER_LITRE` and `SAVINGS_ASSUMPTION` before a presentation with a different scenario.

Daily cost, savings, idle-alert, harsh-event, distance, and idle-minute metrics are materialized with `python -m analytics.batch --date YYYY-MM-DD`. Period API queries aggregate persisted costs for a bounded number of days. Low-utilisation and actual fuel-efficiency costs are not calculated without their required operating baselines.
