#!/usr/bin/env python3
import sys
import os
import argparse
import pandas as pd

def process_report(input_file: str, output_file: str) -> None:
    """
    Cleans and normalizes the RPA output CSV report.
    
    Tasks:
    1. Read the CSV file ensuring leading zeros in CNPJ/CEP are preserved (using string type).
    2. Remove duplicate rows based on the 'cnpj' column.
    3. Normalize text columns: strip whitespace and convert to UPPERCASE.
    4. Save the polished report.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_file}")
        
    print(f"Lendo relatório bruto: {input_file}")
    
    # Read the CSV as strings to avoid stripping leading zeros from CNPJ or CEP
    df = pd.read_csv(input_file, dtype=str)
    
    if df.empty:
        print("Aviso: O arquivo de entrada está vazio. Salvando arquivo vazio.")
        df.to_csv(output_file, index=False)
        return
        
    total_before = len(df)
    
    # Remove duplicate records based on the CNPJ field, keeping the first occurrence
    if 'cnpj' in df.columns:
        # Clean formatting to ensure accurate comparison
        df['cnpj_clean'] = df['cnpj'].str.replace(r'\D', '', regex=True)
        df.drop_duplicates(subset=['cnpj_clean'], keep='first', inplace=True)
        df.drop(columns=['cnpj_clean'], inplace=True)
    else:
        print("Aviso: Coluna 'cnpj' não encontrada. Pulando remoção de duplicatas.")
        
    total_after = len(df)
    duplicates_removed = total_before - total_after
    print(f"Duplicatas removidas: {duplicates_removed}")
    
    # Text columns to normalize (strip and upper)
    text_columns = [
        'razao_social', 'situacao_cadastral', 'cnae_descricao', 
        'logradouro', 'complemento', 'bairro', 'municipio', 'uf'
    ]
    
    # Apply normalization
    for col in df.columns:
        # Check if the column exists in our text columns list, or is of object/string type
        if col in text_columns or df[col].dtype == 'object':
            # Remove leading/trailing whitespaces
            df[col] = df[col].astype(str).str.strip()
            # If in target text columns, convert to uppercase, handle NaN or 'nan' string
            if col in text_columns:
                df[col] = df[col].apply(lambda val: "" if val.lower() in ['nan', 'none', '<nil>'] else val.upper())
                
    # Format CNPJ/CEP to standard format (strip spaces, ensure clean string)
    for col in ['cnpj', 'cep']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    # Save processed DataFrame to CSV
    # Create output directories if they don't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Relatório processado salvo em: {output_file} ({total_after} registros)")

def main() -> None:
    parser = argparse.ArgumentParser(description="Pós-processamento de relatório CSV do GovData Automator.")
    parser.add_argument("input_file", type=str, help="Caminho do arquivo CSV bruto.")
    parser.add_argument("output_file", type=str, help="Caminho do arquivo CSV de saída processado.")
    
    args = parser.parse_args()
    
    try:
        process_report(args.input_file, args.output_file)
        sys.exit(0)
    except Exception as e:
        print(f"Erro no pós-processamento: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
