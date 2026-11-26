"""Regras de validação puras (sem FastAPI nem banco)."""
import re

def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)

def is_valid_cpf(cpf: str) -> bool:
    """Valida um CPF (aceita só dígitos): tamanho, repetição e dígitos verificadores."""
    digits = only_digits(cpf)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    nums = [int(c) for c in digits]
    for n in (9, 10):
        total = sum(nums[i] * (n + 1 - i) for i in range(n))
        check = (total * 10) % 11
        check = 0 if check == 10 else check
        if nums[n] != check:
            return False
    return True

def safe_filename(name: str | None) -> str:
    """Nome de arquivo seguro para guardar e devolver em cabeçalhos HTTP (só ASCII, sem caminho)."""
    base = (name or "").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ ()-]", "_", base).strip(" .")
    return cleaned[:255] or "exam"
