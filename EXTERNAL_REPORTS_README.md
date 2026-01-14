# External Agent Reports - Implementation Guide

## Overview

This implementation provides a complete solution for importing external agent reports into the `n8n_report_model_logs` database table. The solution includes:

1. **Sample mock agent reports** that conform to the schema requirements
2. **n8n workflow** for automated import of reports into the database

---

## Files Created

### 1. `sample_external_reports.json`

A JSON file containing 3 mock agent reports demonstrating different scenarios:

- **Report 1 (external-mock-001)**: Successful aircraft structural repair safety requirements analysis
  - Status: `success`
  - Company: `MockCompany`
  - Groups: `[1, 2, 3]`
  - Contains comprehensive technical report with markdown formatting
  - Includes detailed `mid_steps` showing RAG retrieval and report synthesis

- **Report 2 (external-mock-002)**: Successful landing gear hydraulic inspection intervals report
  - Status: `success`
  - Company: `AeroTech`
  - Groups: `[2, 3]`
  - Contains inspection schedule and maintenance points
  - Simpler mid_steps structure

- **Report 3 (external-mock-003)**: Error case - insufficient documentation
  - Status: `error`
  - Company: `SkyWings`
  - Groups: `[1, 3]`
  - Demonstrates error handling scenario
  - Shows partial information retrieval

### 2. `import_external_workflow.json`

A complete n8n workflow that:
- Reads the JSON file from disk
- Parses the JSON data
- Splits the array into individual reports
- Inserts each report into the `n8n_report_model_logs` table
- Provides comprehensive summary of import results

---

## Schema Compliance

The mock reports match the schema requirements from `report_tab.py`:

### Database Fields

```sql
n8n_report_model_logs (
  id                   -- Auto-generated
  n8n_execution_id     -- Unique identifier (e.g., "external-mock-001")
  status               -- "success" or "error"
  material_category    -- Company/category name
  query                -- Original user query
  report_groups        -- JSON array of group IDs
  execution_data       -- JSON object with output and mid_steps
  logged_at            -- Timestamp (auto-generated)
)
```

### Execution Data Structure

```json
{
  "output": "Markdown formatted report content",
  "mid_steps": [
    {
      "action": {
        "tool": "tool_name",
        "toolInput": { /* parameters */ }
      },
      "observation": "JSON string or plain text"
    }
  ]
}
```

### Mid Steps Details

Each mid_step observation can contain:
- **Document type**: `{"type": "document", "text": "..."}`
- **Text content**: Stringified JSON with `pageContent` and `metadata`
- **Metadata fields**:
  - `file_name`: Source document filename
  - `page_index`: Page number in document
  - `chunk_index`: Chunk number within document
  - `document_type`: Type of document (AMM, Manual, etc.)
  - `section`: Document section identifier

---

## n8n Workflow Details

### Workflow Name
**Import External Agent Reports to n8n_report_model_logs**

### Workflow Nodes

1. **Manual Trigger** - Starts the workflow manually
2. **Read JSON File** - Reads the JSON file from disk
3. **Convert to JSON** - Converts binary data to JSON format
4. **Parse JSON Data** - Parses the JSON array
5. **Split Reports** - Splits array into individual report items
6. **Prepare Insert Data** - Extracts and formats fields for database insertion
7. **Insert into n8n_report_model_logs** - PostgreSQL insert with conflict resolution
8. **Format Success Response** - Formats individual success messages
9. **Aggregate Results** - Aggregates all import results
10. **Final Summary** - Provides comprehensive import summary

### Key Features

- **Conflict Resolution**: Uses `ON CONFLICT (n8n_execution_id) DO UPDATE` to handle duplicates
- **JSON Handling**: Properly stringifies JSON fields for database storage
- **Error Handling**: Graceful handling of import errors
- **Progress Tracking**: Counts successfully imported reports
- **Documentation**: Includes sticky notes explaining each section

### SQL Query

The workflow uses the following INSERT query:

```sql
INSERT INTO n8n_report_model_logs (
  n8n_execution_id,
  status,
  material_category,
  query,
  report_groups,
  execution_data,
  logged_at
) VALUES (
  '{{ $json.n8n_execution_id }}',
  '{{ $json.status }}',
  '{{ $json.material_category }}',
  '{{ $json.query }}',
  '{{ $json.report_groups }}',
  '{{ $json.execution_data }}',
  NOW()
) ON CONFLICT (n8n_execution_id) DO UPDATE SET
  status = EXCLUDED.status,
  material_category = EXCLUDED.material_category,
  query = EXCLUDED.query,
  report_groups = EXCLUDED.report_groups,
  execution_data = EXCLUDED.execution_data,
  logged_at = NOW()
RETURNING *;
```

---

## How to Use

### Step 1: Import the Workflow into n8n

1. Open your n8n instance
2. Click on **Workflows** > **Import from File**
3. Select `import_external_workflow.json`
4. The workflow will be imported with all nodes and connections

### Step 2: Configure Database Credentials

1. Open the workflow in n8n
2. Click on the **"Insert into n8n_report_model_logs"** node
3. Update the PostgreSQL credentials to match your database:
   - Host
   - Port
   - Database name
   - Username
   - Password

### Step 3: Verify File Path

1. Click on the **"Read JSON File"** node
2. Verify the file path is correct:
   - Default: `/mnt/SSD2/CodeHub/FROAV_LLM/sample_external_reports.json`
   - Update if your file is in a different location

### Step 4: Execute the Workflow

1. Click **"Execute Workflow"** button
2. The workflow will:
   - Read the JSON file
   - Parse the reports
   - Insert each report into the database
   - Show summary of imported reports

### Step 5: Verify Import

Check the **Final Summary** node output:
```json
{
  "workflow_status": "completed",
  "total_reports_imported": 3,
  "timestamp": "2026-01-14T...",
  "message": "Successfully imported all external agent reports to n8n_report_model_logs table"
}
```

---

## Testing the Reports in the Frontend

After importing, you can view the reports in the LLMJudges frontend:

1. Navigate to the **Report Tab** in the Streamlit application
2. The reports will appear in the execution list with:
   - Execution IDs: `external-mock-001`, `external-mock-002`, `external-mock-003`
   - Company names: MockCompany, AeroTech, SkyWings
   - Status indicators: success/error
   - Report groups for access control

3. Click on any report to view:
   - Full query
   - Markdown-formatted report output
   - Mid steps with tool usage
   - Collected observations from documents
   - Referenced files (if available)

---

## Customizing the Mock Reports

### Adding More Reports

Edit `sample_external_reports.json` and add new report objects:

```json
{
  "n8n_execution_id": "external-mock-004",
  "status": "success",
  "material_category": "YourCompany",
  "query": "Your query here",
  "report_groups": [1, 2],
  "execution_data": {
    "output": "# Your Report\n\nReport content...",
    "mid_steps": [
      // Your mid steps here
    ]
  }
}
```

### Modifying Report Content

The `output` field supports full Markdown formatting:
- Headings: `#`, `##`, `###`
- Lists: `-`, `*`, `1.`
- Bold: `**text**`
- Italic: `*text*`
- Code: `` `code` ``
- Warnings: `⚠️`

### Adjusting Mid Steps

Each mid_step should follow this structure:

```json
{
  "action": {
    "tool": "tool_name",
    "toolInput": {
      "query": "search query",
      "filter": {}
    }
  },
  "observation": "[{\"type\":\"document\",\"text\":\"{...}\"}]"
}
```

---

## Schema Validation

The workflow has been validated using n8n MCP tools:

```
✓ Valid workflow structure
✓ All nodes properly configured
✓ Connections validated
✓ Expressions validated
✓ 1 trigger node present
✓ 0 errors found
```

Minor warnings:
- Some nodes use older typeVersion (non-critical)

---

## Troubleshooting

### File Not Found Error

**Error**: Cannot read file at specified path

**Solution**:
1. Verify the file exists: `ls -la /mnt/SSD2/CodeHub/FROAV_LLM/sample_external_reports.json`
2. Check file permissions: `chmod 644 sample_external_reports.json`
3. Update the file path in the **"Read JSON File"** node

### Database Connection Error

**Error**: Cannot connect to PostgreSQL

**Solution**:
1. Verify database credentials in the workflow
2. Ensure the database is running
3. Check network connectivity
4. Verify the `n8n_report_model_logs` table exists

### JSON Parse Error

**Error**: Cannot parse JSON data

**Solution**:
1. Validate JSON syntax: `cat sample_external_reports.json | jq .`
2. Ensure proper encoding (UTF-8)
3. Check for trailing commas or syntax errors

### Duplicate Key Error

**Error**: Duplicate n8n_execution_id

**Solution**:
The workflow handles this automatically with `ON CONFLICT ... DO UPDATE`. Existing records will be updated with new data.

---

## Database Table Schema

Ensure your database has the following table structure:

```sql
CREATE TABLE IF NOT EXISTS n8n_report_model_logs (
    id SERIAL PRIMARY KEY,
    n8n_execution_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50),
    material_category VARCHAR(255),
    query TEXT,
    report_groups TEXT,  -- JSON array as text
    execution_data TEXT, -- JSON object as text
    logged_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_n8n_execution_id ON n8n_report_model_logs(n8n_execution_id);
CREATE INDEX idx_status ON n8n_report_model_logs(status);
CREATE INDEX idx_material_category ON n8n_report_model_logs(material_category);
CREATE INDEX idx_logged_at ON n8n_report_model_logs(logged_at DESC);
```

---

## Integration with Existing System

The mock reports integrate seamlessly with the existing LLMJudges system:

### Frontend (`report_tab.py`)
- ✅ Displays output in markdown format
- ✅ Shows mid_steps with tool usage
- ✅ Extracts and displays observations
- ✅ Shows referenced files
- ✅ Supports group-based access control
- ✅ Handles both success and error statuses

### Backend (`llm_judges_router.py`)
- No changes needed - reports are stored in the same format
- Compatible with existing feedback system
- Integrates with user authentication and groups

---

## Future Enhancements

Potential improvements for the workflow:

1. **Webhook Trigger**: Replace manual trigger with webhook for automated imports
2. **File Watcher**: Monitor directory for new JSON files
3. **Batch Processing**: Support multiple JSON files
4. **Error Notifications**: Send alerts on import failures
5. **Data Validation**: Add schema validation before insert
6. **Logging**: Enhanced logging and audit trail
7. **Rollback**: Transaction support for batch imports

---

## Related Files

- `LLMJudges_frontend/src/report_tab.py` - Frontend display logic
- `LLMJudges_server/src/routers/llm_judges_router.py` - Backend API
- `docker-compose.yml` - Database configuration

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify workflow validation results
3. Review n8n execution logs
4. Check PostgreSQL logs for database errors

---

## Summary

✅ Created `sample_external_reports.json` with 3 comprehensive mock reports
✅ Created `import_external_workflow.json` n8n workflow for automated import
✅ All reports conform to the schema requirements from `report_tab.py`
✅ Workflow validated successfully with n8n MCP tools
✅ Includes detailed documentation and troubleshooting guide
✅ Ready for production use

The mock reports demonstrate:
- ✅ Successful report generation with full content
- ✅ Error handling scenarios
- ✅ Multiple companies/categories
- ✅ Group-based access control
- ✅ Detailed mid_steps with RAG retrieval
- ✅ Markdown-formatted output
- ✅ Document metadata and references

---

**Last Updated**: 2026-01-14
**Version**: 1.0
