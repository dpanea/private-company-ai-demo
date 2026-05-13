CREATE TABLE IF NOT EXISTS users_or_owners (
    user_id text PRIMARY KEY,
    name text NOT NULL,
    email text,
    is_active boolean NOT NULL DEFAULT true,
    profile_or_role text,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id text PRIMARY KEY,
    account_name text NOT NULL,
    account_type text,
    industry text,
    website text,
    phone text,
    billing_country text,
    billing_city text,
    owner_id text REFERENCES users_or_owners(user_id),
    parent_account_id text REFERENCES accounts(account_id),
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id),
    name text NOT NULL,
    first_name text,
    last_name text,
    email text,
    phone text,
    mobile_phone text,
    title text,
    role_or_department text,
    owner_id text REFERENCES users_or_owners(user_id),
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id),
    primary_contact_id text REFERENCES contacts(contact_id),
    contract_id text,
    name text NOT NULL,
    stage text,
    amount numeric,
    currency text,
    probability numeric,
    close_date date,
    is_closed boolean,
    is_won boolean,
    owner_id text REFERENCES users_or_owners(user_id),
    record_type_id text,
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE TABLE IF NOT EXISTS contracts (
    contract_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id),
    opportunity_id_if_available text REFERENCES opportunities(opportunity_id),
    contract_number text NOT NULL,
    status text,
    start_date date,
    end_date date,
    activated_date date,
    customer_signed_contact_id text REFERENCES contacts(contact_id),
    owner_id text REFERENCES users_or_owners(user_id),
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE TABLE IF NOT EXISTS activities (
    activity_id text PRIMARY KEY,
    source_object text NOT NULL CHECK (source_object IN ('Task', 'Event')),
    account_id text REFERENCES accounts(account_id),
    opportunity_id text REFERENCES opportunities(opportunity_id),
    contact_id text REFERENCES contacts(contact_id),
    lead_id text,
    contract_id text REFERENCES contracts(contract_id),
    who_id text,
    what_id text,
    owner_id text REFERENCES users_or_owners(user_id),
    subject text,
    activity_type text,
    subtype text,
    status text,
    priority text,
    activity_date date,
    start_datetime timestamptz,
    end_datetime timestamptz,
    description text,
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE INDEX IF NOT EXISTS idx_contacts_account_id ON contacts(account_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_account_id ON opportunities(account_id);
CREATE INDEX IF NOT EXISTS idx_contracts_account_id ON contracts(account_id);
CREATE INDEX IF NOT EXISTS idx_activities_account_id ON activities(account_id);
CREATE INDEX IF NOT EXISTS idx_activities_opportunity_id ON activities(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_activities_activity_date ON activities(activity_date);
