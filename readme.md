
# FROAV:Framework for RAG Observation and Agent Verification

## Project Overview
**FROAV** is an advanced document analysis ecosystem designed to bridge the gap between autonomous AI agents and human expertise. While initially focused on analyzing complex financial filings (SEC 10-K, 10-Q, 8-K), the platform is material-agnostic and adaptable to any domain requiring deep semantic analysis. 

It leverages a multi-stage **Retrieval-Augmented Generation (RAG)** workflow to analyze documents and subjects the results to a rigorous "LLM-as-a-Judge" evaluation process.

By integrating **n8n** for orchestration, **PostgreSQL** for granular data management, **FastAPI** for backend logic, and **Streamlit** for human interaction, FROAV provides a transparent laboratory for researchers to experiment with prompts, refine RAG strategies, and validate agent performance.

## 🎯 Good Scenarios
- ⏳ If you don't want to spend hundreds of hours to implement infrastructures for your LLM agent analysis
- 🔬 If you don't have much understanding of frontend, backend, and database but you are a good researcher and just want to focus on what you are interested in

### ✨ This is for you!

## 🚀 FROAV provides
🎥 [Demo video](https://youtu.be/w-SyxT03ySA)
#### 📊 Clean interface of user feedback, agent report, and LLM judgement display
<img width="640" height="360" alt="Snapshot_3" src="https://github.com/user-attachments/assets/37e0f801-08bb-4950-8bc0-b474a2a04ac8" />
<img width="640" height="360" alt="Snapshot_4" src="https://github.com/user-attachments/assets/bfee97c2-6ad1-4bcc-a253-1d6be20fb80d" />
<img width="640" height="360" alt="Snapshot_5" src="https://github.com/user-attachments/assets/c2a70fc1-0c5b-4c03-af0d-6965fa9b593c" />
<img width="640" height="360" alt="Snapshot_1" src="https://github.com/user-attachments/assets/a3f2d7d7-5e6e-481b-acb4-9f541dd5ac41" />

#### ⚡ No code needed GUI workflow control empowered by n8n and its great community
<img width="640" height="360" alt="Snapshot_6" src="https://github.com/user-attachments/assets/7ca82969-0987-4629-b16d-9cc19c8f575f" />
<img width="640" height="360" alt="Snapshot_2" src="https://github.com/user-attachments/assets/81e7c454-cace-45e3-bb66-1fe8ae7843d1" />

#### 🐍 Easy customization for any Python code logic
<img width="640" height="360" alt="螢幕擷取畫面 2026-01-10 081646" src="https://github.com/user-attachments/assets/c5f3f6b6-d69d-499f-8a08-48c0a86f9e81" />

## Prerequisite
- Docker
- Docker compose



## Installation
================================================================================

🎥 [Full guide video](https://youtu.be/ZKT5elbM46Y)

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

2. Specify the material categories you want to use in the data node and upload RAG materials.
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
