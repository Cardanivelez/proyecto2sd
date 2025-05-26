#!/bin/bash

# Detener procesos previos si existen
pkill -f "src/namenode/server.py"
pkill -f "src/datanode/server.py"

# Crear directorios de almacenamiento
mkdir -p data/{node1,node2,node3}

# Limpiar logs antiguos
rm -f *.log

# Activar entorno virtual
source venv/bin/activate

# Iniciar NameNode
echo "Iniciando NameNode..."
nohup python3 src/namenode/server.py > namenode.log 2>&1 &

# Esperar a que el NameNode esté listo
sleep 2

# Iniciar DataNodes
echo "Iniciando DataNodes..."
nohup python3 src/datanode/server.py --node-id datanode1 --port 50051 --storage ./data/node1 > datanode1.log 2>&1 &
nohup python3 src/datanode/server.py --node-id datanode2 --port 50052 --storage ./data/node2 > datanode2.log 2>&1 &
nohup python3 src/datanode/server.py --node-id datanode3 --port 50053 --storage ./data/node3 > datanode3.log 2>&1 &

echo "Esperando a que los servicios estén listos..."
sleep 3

# Verificar que todos los servicios están corriendo
if pgrep -f "src/namenode/server.py" > /dev/null && pgrep -f "src/datanode/server.py" > /dev/null; then
    echo "Cluster iniciado correctamente"
else
    echo "Error: No se pudieron iniciar todos los servicios"
    exit 1
fi

# Mostrar logs en tiempo real
tail -f *.log