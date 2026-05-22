import hashlib

# Uma chave secreta só nossa para tornar os hashes impossíveis de quebrar
SALT = "ascend_super_secret_key_2026"


def gerar_hash_senha(senha_pura: str) -> str:
    """Transforma a senha em um hash SHA-256 seguro usando um Salt."""
    senha_com_salt = senha_pura + SALT
    # Transforma o texto em bytes, gera o hash e converte de volta para texto (hex)
    return hashlib.sha256(senha_com_salt.encode('utf-8')).hexdigest()


def verificar_senha(senha_pura: str, senha_criptografada: str) -> bool:
    """Compara a senha digitada com o hash que está no banco."""
    # Gera o hash da senha que o usuário acabou de digitar e compara com o do banco
    return gerar_hash_senha(senha_pura) == senha_criptografada
