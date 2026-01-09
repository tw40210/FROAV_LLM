
## Prerequisite
- Docker
- Docker compose



## Installation
================================================================================

1. Setup `LLMJudges_server/src/config/.env` and `LLMJudges_frontend/src/config/.env` 
```
#As you have in docker-compose.yml
PGPASSWORD=mysecretpassword 
PGHOST=postgres 
PGHOST_CLUSTER=postgres
PGPORT=5432 
PGDATABASE=n8n 
PGUSER=n8n 
```

2. `docker compose up`
3. `docker cp ./workflows.json froav_llm-n8n-1:/home/node/.n8n/workflows.json`
4. `docker exec -it froav_llm-n8n-1 n8n import:workflow --input=/home/node/.n8n/workflows.json`

5. Create postgres tables (run commands in local terminal)
```
echo "CREATE TABLE n8n_report_model_logs (
    id SERIAL PRIMARY KEY,
    n8n_execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id VARCHAR(255),
    status VARCHAR(50),
    execution_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    material_category VARCHAR(50),
    report_groups TEXT
);" | docker exec -i froav_llm-postgres-1 psql -U n8n -d n8n
```


```
echo "CREATE TABLE n8n_llm_judgement_logs (
    id integer,
    judge_n8n_execution_id VARCHAR(255) UNIQUE NOT NULL,
    report_n8n_execution_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    judgement_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    material_category VARCHAR(50)
);" | docker exec -i froav_llm-postgres-1 psql -U n8n -d n8n
```


```
echo "CREATE TABLE report_human_feedback (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,
    report_n8n_execution_id VARCHAR(255) NOT NULL,
    human_feedback_data JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    query TEXT,
    material_category VARCHAR(50)
);" | docker exec -i froav_llm-postgres-1 psql -U n8n -d n8n
```


```
echo "CREATE TABLE user_data (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(255) UNIQUE NOT NULL,
    user_token VARCHAR(255) NOT NULL,
    user_groups TEXT, 
    description TEXT, 
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);" | docker exec -i froav_llm-postgres-1 psql -U n8n -d n8n
```

7. N8n Credentials
```
# Postgres Node
Host: postgres
Database: n8n
User: n8n
Password: {your_postgres_password_docker_compose}
SSL: Disable
Port: 5432
```

* OpenRouter
https://youtu.be/rQ039ga-Zsc?si=jz_eYiupcPRA3MYo&t=310
* Openai (for RAG embedding)
https://www.youtube.com/watch?v=9uJS6kvfNDE
* Supabase (RAG)
https://www.youtube.com/watch?v=H7Lad7tVFUI
* Setup RAG table
https://docs.langchain.com/oss/javascript/integrations/vectorstores/supabase
* Troubleshooting:
If you get a credential error after updating, try clicking the nodes, re-selecting the model and saving workflow again.


Launch
================================================================================
n8n server url: http://localhost:5678/
frontend url: http://localhost:8501/


1. Prepare financial filings in `LLMJudges_server/data/company_data/{material_category}`
File name should be `{material_category}_{material_type}_{years}.pdf` ex:`META_10K_2022.pdf`

2. Upload RAG materials
3. Generate agent reports
4. Generate LLM judgements
5. Get expert feedbacks

## Customization
================================================================================

### How to add a new model
1. Add a new model node in `Template Judgment Sub-workflow (3 Models)` and link it to `Merge All Judgments` node.
2. Add a new model name in `Financial Report Multi-LLM Judge System (OpenRouter) v2` - `Calculate Final Score & Report` node. Like
```
const models = [
        'Deepseek 3.2 (Model 1)',
        'Deepseek 3.1 (Model 2)'
      ]
```