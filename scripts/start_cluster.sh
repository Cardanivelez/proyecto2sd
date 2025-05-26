#!/bin/bash

# Detener procesos previos si existen
pkill -f "dfs-namenode"
pkill -f "dfs-datanode"

# Crear directorios de almacenamiento
mkdir -p data/{node1,node2,node3}

# Limpiar logs antiguos
rm -f *.log

# Iniciar NameNode
echo "Iniciando NameNode..."
poetry run dfs-namenode > namenode.log 2>&1 &

# Esperar a que el NameNode esté listo
sleep 2

# Iniciar DataNodes
echo "Iniciando DataNodes..."
poetry run dfs-datanode --node-id datanode1 --port 50051 --storage ./data/node1 > datanode1.log 2>&1 &
poetry run dfs-datanode --node-id datanode2 --port 50052 --storage ./data/node2 > datanode2.log 2>&1 &
poetry run dfs-datanode --node-id datanode3 --port 50053 --storage ./data/node3 > datanode3.log 2>&1 &

echo "Esperando a que los servicios estén listos..."
sleep 3

# Verificar que todos los servicios están corriendo
if pgrep -f "dfs-namenode" > /dev/null && pgrep -f "dfs-datanode" > /dev/null; then
    echo "Cluster iniciado correctamente"
else
    echo "Error: No se pudieron iniciar todos los servicios"
    exit 1
fi

# Mostrar logs en tiempo real
tail -f *.log