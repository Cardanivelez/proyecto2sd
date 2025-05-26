# Sistema de Archivos Distribuidos con Replicación

## Descripción
Sistema de archivos distribuidos implementado en Python con soporte para replicación de datos.

## Características
- NameNode para gestión de metadatos
- DataNodes con replicación de bloques
- Cliente CLI para operaciones básicas
- Factor de replicación configurable


## Instalación
```bash
# Clonar el repositorio
git clone <url-repositorio>
cd dfs

# Instalar dependencias
poetry install

# Generar código gRPC
./scripts/generate_grpc.sh