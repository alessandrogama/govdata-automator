#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import random
import string
import uuid
import datetime
import urllib.request
import urllib.error

# Paths inside the container
WORKFLOW_DIR = "/data/n8n/workflows"
DB_PATH = "/home/node/.n8n/database.sqlite"

def generate_n8n_id() -> str:
    """Generates a random 16-character alphanumeric ID similar to n8n default IDs."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=16))

def load_workflow_file(filename: str) -> dict:
    filepath = os.path.join(WORKFLOW_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Erro: Arquivo não encontrado em {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_workflow_file(filename: str, data: dict) -> None:
    filepath = os.path.join(WORKFLOW_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_sqlite_bootstrap() -> None:
    """Performs the bootstrap by directly inserting/updating the SQLite database."""
    print("Iniciando bootstrap via injeção direta no banco SQLite...")
    
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados SQLite do n8n não encontrado em {DB_PATH}", file=sys.stderr)
        print("Certifique-se de que o n8n já foi iniciado e inicializou o banco.", file=sys.stderr)
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load flows
    cnpj_flow = load_workflow_file("cnpj_flow.json")
    cep_flow = load_workflow_file("cep_flow.json")
    main_flow = load_workflow_file("main_flow.json")
    
    # Check if they already exist in the database to reuse their IDs (prevent duplicates)
    cursor.execute("SELECT id, name FROM workflow_entity WHERE name IN ('cnpj_flow', 'cep_flow', 'main_flow')")
    existing = {name: uid for uid, name in cursor.fetchall()}
    
    cnpj_id = existing.get("cnpj_flow", generate_n8n_id())
    cep_id = existing.get("cep_flow", generate_n8n_id())
    main_id = existing.get("main_flow", generate_n8n_id())
    
    print(f"-> Mapeando cnpj_flow para ID: {cnpj_id}")
    print(f"-> Mapeando cep_flow para ID: {cep_id}")
    print(f"-> Mapeando main_flow para ID: {main_id}")
    
    # Update main_flow references to sub-workflows in memory
    main_flow_str = json.dumps(main_flow)
    main_flow_str = main_flow_str.replace('"workflowId": "cnpj_flow"', f'"workflowId": "{cnpj_id}"')
    main_flow_str = main_flow_str.replace('"workflowId": "cep_flow"', f'"workflowId": "{cep_id}"')
    main_flow_updated = json.loads(main_flow_str)
    
    # Save the updated main_flow back to disk so the host file is synced
    save_workflow_file("main_flow.json", main_flow_updated)
    print("-> Arquivo main_flow.json atualizado com as referências corretas no disco.")
    
    # Helper to insert or update the workflow row
    def upsert_workflow(uid: str, name: str, flow_data: dict, active_status: int):
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Check if ID exists to do UPDATE or INSERT
        cursor.execute("SELECT 1 FROM workflow_entity WHERE id = ?", (uid,))
        exists = cursor.fetchone()
        
        nodes_json = json.dumps(flow_data.get("nodes", []))
        connections_json = json.dumps(flow_data.get("connections", {}))
        settings_json = json.dumps(flow_data.get("settings", {}))
        meta_json = json.dumps(flow_data.get("meta", {}))
        version_id = str(uuid.uuid4())
        
        if exists:
            # Update
            cursor.execute("""
                UPDATE workflow_entity 
                SET name = ?, active = ?, nodes = ?, connections = ?, settings = ?, meta = ?, updatedAt = ?, versionId = ?
                WHERE id = ?
            """, (name, active_status, nodes_json, connections_json, settings_json, meta_json, now_iso, version_id, uid))
            print(f"   [Atualizado] Workflow '{name}' atualizado no banco.")
        else:
            # Insert
            cursor.execute("""
                INSERT INTO workflow_entity 
                (id, name, active, nodes, connections, settings, staticData, pinData, versionId, triggerCount, meta, parentFolderId, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, 0, ?, NULL, ?, ?)
            """, (uid, name, active_status, nodes_json, connections_json, settings_json, version_id, meta_json, now_iso, now_iso))
            print(f"   [Criado] Workflow '{name}' inserido no banco.")
            
    # Upsert the workflows (activating all of them)
    upsert_workflow(cnpj_id, "cnpj_flow", cnpj_flow, 1)
    upsert_workflow(cep_id, "cep_flow", cep_flow, 1)
    upsert_workflow(main_id, "main_flow", main_flow_updated, 1)
    
    conn.commit()
    conn.close()
    print("Bootstrap via SQLite concluído com sucesso!")

def run_api_bootstrap(api_key: str, port: str) -> None:
    """Performs the bootstrap using n8n REST API."""
    print("Iniciando bootstrap via API REST do n8n...")
    base_url = f"http://localhost:{port}/api/v1/workflows"
    
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # Load flows
    cnpj_flow = load_workflow_file("cnpj_flow.json")
    cep_flow = load_workflow_file("cep_flow.json")
    main_flow = load_workflow_file("main_flow.json")
    
    def send_post(url, data):
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))
            
    def send_put(url, data):
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))

    try:
        # 1. Create cnpj_flow
        print("-> Enviando cnpj_flow para a API...")
        cnpj_flow_res = send_post(base_url, {
            "name": "cnpj_flow",
            "nodes": cnpj_flow.get("nodes", []),
            "connections": cnpj_flow.get("connections", {}),
            "settings": cnpj_flow.get("settings", {})
        })
        cnpj_id = cnpj_flow_res["id"]
        print(f"   [Criado] ID: {cnpj_id}")
        
        # 2. Create cep_flow
        print("-> Enviando cep_flow para a API...")
        cep_flow_res = send_post(base_url, {
            "name": "cep_flow",
            "nodes": cep_flow.get("nodes", []),
            "connections": cep_flow.get("connections", {}),
            "settings": cep_flow.get("settings", {})
        })
        cep_id = cep_flow_res["id"]
        print(f"   [Criado] ID: {cep_id}")
        
        # 3. Update main_flow JSON
        main_flow_str = json.dumps(main_flow)
        main_flow_str = main_flow_str.replace('"workflowId": "cnpj_flow"', f'"workflowId": "{cnpj_id}"')
        main_flow_str = main_flow_str.replace('"workflowId": "cep_flow"', f'"workflowId": "{cep_id}"')
        main_flow_updated = json.loads(main_flow_str)
        
        save_workflow_file("main_flow.json", main_flow_updated)
        print("-> Arquivo main_flow.json atualizado com as referências corretas no disco.")
        
        # 4. Create main_flow
        print("-> Enviando main_flow para a API...")
        main_flow_res = send_post(base_url, {
            "name": "main_flow",
            "nodes": main_flow_updated.get("nodes", []),
            "connections": main_flow_updated.get("connections", {}),
            "settings": main_flow_updated.get("settings", {})
        })
        main_id = main_flow_res["id"]
        print(f"   [Criado] ID: {main_id}")
        
        # 5. Activate workflows
        print("-> Ativando workflows...")
        send_put(f"{base_url}/{cnpj_id}", {"active": True})
        send_put(f"{base_url}/{cep_id}", {"active": True})
        send_put(f"{base_url}/{main_id}", {"active": True})
        
        print("Bootstrap via API REST concluído com sucesso!")
        
    except urllib.error.HTTPError as e:
        print(f"Erro na API do n8n: {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado no bootstrap via API: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    # Check if API key is provided (either from environment variable directly or n8n/.env file)
    api_key = os.environ.get("N8N_API_KEY")
    port = os.environ.get("N8N_PORT", "5678")
    
    # Try reading from n8n/.env if present
    env_path = "/data/n8n/.env"
    if not api_key and os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("N8N_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                elif line.startswith("N8N_PORT="):
                    port = line.split("=", 1)[1].strip()
                    
    if api_key:
        run_api_bootstrap(api_key, port)
    else:
        # If no API key, fallback to direct SQLite DB modification
        run_sqlite_bootstrap()

if __name__ == "__main__":
    main()
