We use docker compose to manage n8n and postgres and keep python cli and streamlit local for easy debugging.

* Rebuild:
docker compose up -d --no-deps --build


* Installation:
1. uv
2. .env
3. import workflow.json (Docs: backup n8n)
4. postgres: credential, create tables


* TODO:
1. SEC summary reports
2. survey system
3. database for survey



* Create the new table with your updated schema
```bash
CREATE TABLE n8n_report_model_logs (
    id SERIAL PRIMARY KEY,
    n8n_execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255),
    status VARCHAR(50),
    execution_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    company_ticker VARCHAR(50),
    report_groups TEXT
);
```

```bash
CREATE TABLE n8n_llm_judgement_logs (
    id integer,
    judge_n8n_execution_id VARCHAR(255) UNIQUE NOT NULL,
    report_n8n_execution_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    judgement_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    company_ticker VARCHAR(50)
);
```

```bash
CREATE TABLE report_human_feedback (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,
    report_n8n_execution_id VARCHAR(255) NOT NULL,
    human_feedback_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    company_ticker VARCHAR(50)
);
```

```bash
CREATE TABLE user_data (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(255) UNIQUE NOT NULL,
    user_token VARCHAR(255) NOT NULL,
    user_groups TEXT, 
    description TEXT, 
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

