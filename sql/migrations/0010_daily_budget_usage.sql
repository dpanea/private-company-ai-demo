CREATE TABLE IF NOT EXISTS daily_budget_usage (
    usage_date date PRIMARY KEY,
    tokens_in integer NOT NULL DEFAULT 0,
    tokens_out integer NOT NULL DEFAULT 0,
    cost_estimate_eur numeric NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);
