#!/bin/bash

# Cargar configuración
source config/cluster_config.yaml

# Verificar NameNode
echo "Verificando NameNode..."
curl -s http://${NAMENODE_HOST}:${NAMENODE_PORT}/health || echo "NameNode no responde"

# Verificar DataNodes
for node in "${!DATANODES[@]}"; do
    echo "Verificando DataNode $node..."
    host=${DATANODES[$node]%%:*}
    port=${DATANODES[$node]#*:}
    nc -zv $host $port 2>&1 || echo "DataNode $node no responde"
done