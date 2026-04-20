# Vault Configuration for OpenClaw Tokens
# Self-hosted HashiCorp Vault (free, runs in Docker)

ui            = true
disable_mlock = true

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = true  # Use TLS in production with proper certificates
}

storage "file" {
  path = "/vault/data"
}
