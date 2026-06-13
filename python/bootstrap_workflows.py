#!/usr/bin/env python3
import os
import sys
import json
import time
import requests

# Resolve paths dynamically relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
WORKFLOW_DIR = os.path.join(PROJECT_ROOT, "n8n", "workflows")

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

def check_n8n_health(host: str, port: str) -> bool:
    """Checks if n8n is up and running by polling the healthz endpoint."""
    health_url = f"http://{host}:{port}/healthz"
    max_retries = 10
    retry_interval = 2
    
    print(f"Verificando a conectividade com o n8n em {health_url}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(health_url, timeout=5)
            if res.status_code == 200:
                print("n8n está pronto e respondendo!")
                return True
        except Exception:
            pass
        
        print(f"   [Tentativa {attempt}/{max_retries}] n8n não respondeu. Aguardando {retry_interval}s...")
        time.sleep(retry_interval)
        
    return False

def run_api_bootstrap(api_key: str, host: str, port: str) -> None:
    """Performs the workflow bootstrap using the n8n REST API."""
    # Step 0: Ensure n8n is reachable
    if not check_n8n_health(host, port):
        print("Erro: n8n não está acessível. Certifique-se de que o container está rodando.", file=sys.stderr)
        sys.exit(1)
        
    print("Iniciando bootstrap via API REST do n8n...")
    base_url = f"http://{host}:{port}/api/v1/workflows"
    
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # Load flows
    cnpj_flow = load_workflow_file("cnpj_flow.json")
    cep_flow = load_workflow_file("cep_flow.json")
    main_flow = load_workflow_file("main_flow.json")
    
    try:
        # 1. Create cnpj_flow
        print("-> Enviando cnpj_flow para a API...")
        res = requests.post(base_url, headers=headers, json={
            "name": "cnpj_flow",
            "nodes": cnpj_flow.get("nodes", []),
            "connections": cnpj_flow.get("connections", {}),
            "settings": cnpj_flow.get("settings", {})
        })
        res.raise_for_status()
        cnpj_id = res.json()["id"]
        print(f"   [Criado] ID: {cnpj_id}")
        
        # 2. Create cep_flow
        print("-> Enviando cep_flow para a API...")
        res = requests.post(base_url, headers=headers, json={
            "name": "cep_flow",
            "nodes": cep_flow.get("nodes", []),
            "connections": cep_flow.get("connections", {}),
            "settings": cep_flow.get("settings", {})
        })
        res.raise_for_status()
        cep_id = res.json()["id"]
        print(f"   [Criado] ID: {cep_id}")
        
        # 3. Update main_flow JSON with correct workflow IDs
        main_flow_str = json.dumps(main_flow)
        main_flow_str = main_flow_str.replace('"workflowId": "cnpj_flow"', f'"workflowId": "{cnpj_id}"')
        main_flow_str = main_flow_str.replace('"workflowId": "cep_flow"', f'"workflowId": "{cep_id}"')
        main_flow_updated = json.loads(main_flow_str)
        
        save_workflow_file("main_flow.json", main_flow_updated)
        print("-> Arquivo main_flow.json atualizado com as referências corretas no disco.")
        
        # 4. Create main_flow
        print("-> Enviando main_flow para a API...")
        res = requests.post(base_url, headers=headers, json={
            "name": "main_flow",
            "nodes": main_flow_updated.get("nodes", []),
            "connections": main_flow_updated.get("connections", {}),
            "settings": main_flow_updated.get("settings", {})
        })
        res.raise_for_status()
        main_id = res.json()["id"]
        print(f"   [Criado] ID: {main_id}")
        
        # 5. Activate workflows using the correct POST /api/v1/workflows/{id}/activate endpoint
        print("-> Ativando workflows...")
        for uid in [cnpj_id, cep_id, main_id]:
            act_res = requests.post(f"{base_url}/{uid}/activate", headers=headers, json={})
            act_res.raise_for_status()
        
        print("Bootstrap via API REST concluído com sucesso!")
        
    except requests.exceptions.HTTPError as e:
        print(f"Erro na API do n8n: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado no bootstrap: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    api_key = os.environ.get("N8N_API_KEY")
    n8n_host = os.environ.get("N8N_HOST", "localhost")
    port = os.environ.get("N8N_PORT", "5678")
    
    # Check if N8N_API_KEY is not found or empty
    if not api_key or api_key.strip() == "":
        print("⚠️  N8N_API_KEY não encontrada no n8n/.env")
        print("   Passos:")
        print("   1. Acesse http://localhost:5678")
        print("   2. Crie sua conta admin")
        print("   3. Vá em Settings → API → crie uma API Key")
        print("   4. Adicione N8N_API_KEY=sua_key no arquivo n8n/.env")
        print("   5. Execute: docker compose restart bootstrap")
        sys.exit(0)
        
    print("✅ API Key encontrada. Iniciando bootstrap...")
    run_api_bootstrap(api_key, n8n_host, port)

if __name__ == "__main__":
    main()
