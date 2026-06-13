#!/usr/bin/env python3
import sys
import json
import argparse
import re

def validate_cnpj(cnpj: str) -> bool:
    """
    Validates a Brazilian CNPJ (Cadastro Nacional da Pessoa Jurídica) using check digits.
    
    Args:
        cnpj: The CNPJ string to be validated. Can be formatted or raw.
        
    Returns:
        bool: True if the CNPJ is mathematically valid, False otherwise.
    """
    # Clean non-digit characters
    cleaned = re.sub(r'\D', '', cnpj)
    
    # Check length
    if len(cleaned) != 14:
        return False
        
    # Check for known invalid identical digits sequences (e.g., 00000000000000, 11111111111111, etc.)
    if len(set(cleaned)) == 1:
        return False
        
    # Weights for the first validation digit
    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    # Calculate first verification digit
    sum_first = sum(int(cleaned[i]) * weights_first[i] for i in range(12))
    remainder_first = sum_first % 11
    digit_first = 0 if remainder_first < 2 else 11 - remainder_first
    
    # Check if first digit matches
    if int(cleaned[12]) != digit_first:
        return False
        
    # Weights for the second validation digit
    weights_second = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    # Calculate second verification digit
    sum_second = sum(int(cleaned[i]) * weights_second[i] for i in range(13))
    remainder_second = sum_second % 11
    digit_second = 0 if remainder_second < 2 else 11 - remainder_second
    
    # Check if second digit matches
    if int(cleaned[13]) != digit_second:
        return False
        
    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Validador de CNPJ por dígito verificador.")
    parser.add_argument("cnpj", type=str, nargs="?", help="O CNPJ a ser validado.")
    args = parser.parse_args()
    
    # If CNPJ was not provided via arguments, read from stdin (optional utility)
    cnpj_input = args.cnpj
    if not cnpj_input:
        if not sys.stdin.isatty():
            cnpj_input = sys.stdin.read(1000).strip()
        else:
            print(json.dumps({"error": "CNPJ não fornecido"}), file=sys.stderr)
            sys.exit(1)
            
    is_valid = validate_cnpj(cnpj_input)
    
    # Print JSON output to stdout
    result = {
        "cnpj": cnpj_input,
        "cleaned": re.sub(r'\D', '', cnpj_input),
        "valid": is_valid
    }
    
    print(json.dumps(result))
    
    # Exit with code 0 if valid, 1 if invalid (helpful for scripting/cli tools)
    if not is_valid:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
