#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
import urllib.error

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

def check_n8n_health(port: str) -> bool:
    """Checks if n8n is up and running by polling the healthz endpoint."""
    health_url = f"http://localhost:{port}/healthz"
    max_retries = 10
    retry_interval = 2
    
    print(f"Verificando a conectividade com o n8n em {health_url}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(health_url, timeout=5) as res:
                if res.status == 200:
                    print("n8n está pronto e respondendo!")
                    return True
        except Exception:
            pass
        
        print(f"   [Tentativa {attempt}/{max_retries}] n8n não respondeu. Aguardando {retry_interval}s...")
        time.sleep(retry_interval)
        
    return False

def run_api_bootstrap(api_key: str, port: str) -> None:
    """Performs the workflow bootstrap using the n8n REST API."""
    # Step 0: Ensure n8n is reachable
    if not check_n8n_health(port):
        print("Erro: n8n não está acessível. Certifique-se de que o container está rodando.", file=sys.stderr)
        sys.exit(1)
        
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
            
    def send_activate(workflow_id):
        # In n8n 1.x, activation is done via POST /api/v1/workflows/{id}/activate
        url = f"{base_url}/{workflow_id}/activate"
        req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
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
        
        # 3. Update main_flow JSON with correct workflow IDs
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
        
        # 5. Activate workflows using the correct /activate endpoint
        print("-> Ativando workflows...")
        send_activate(cnpj_id)
        send_activate(cep_id)
        send_activate(main_id)
        
        print("Bootstrap via API REST concluído com sucesso!")
        
    except urllib.error.HTTPError as e:
        print(f"Erro na API do n8n: {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado no bootstrap: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    # 1. Attempt to read N8N_API_KEY from environment variables
    api_key = os.environ.get("N8N_API_KEY")
    port = os.environ.get("N8N_PORT", "5678")
    
    # 2. Fallback to check n8n/.env file if key is not in environment
    env_paths = [
        os.path.join(PROJECT_ROOT, "n8n", ".env"),
        os.path.join(PROJECT_ROOT, ".env"),
        "/data/n8n/.env"
    ]
    
    if not api_key:
        for env_path in env_paths:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("N8N_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                        elif line.startswith("N8N_PORT="):
                            port = line.split("=", 1)[1].strip()
                if api_key:
                    break
                    
    if not api_key:
        print("Erro: N8N_API_KEY não foi encontrada nas variáveis de ambiente nem no arquivo n8n/.env.", file=sys.stderr)
        print("Por favor, declare N8N_API_KEY no ambiente ou arquivo n8n/.env para prosseguir.", file=sys.stderr)
        sys.exit(1)
        
    run_api_bootstrap(api_key, port)

if __name__ == "__main__":
    main()
