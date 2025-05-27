# Sistema de Archivos Distribuidos por Bloques (DFS)

## Descripción General
Este proyecto implementa un **sistema de archivos distribuidos minimalista basado en bloques**, inspirado en arquitecturas como GFS y HDFS. Permite compartir y acceder concurrentemente a archivos almacenados en diferentes nodos, garantizando replicación, tolerancia a fallos y acceso eficiente mediante una interfaz de línea de comandos (CLI).

### Objetivo
Diseñar e implementar un DFS que distribuya archivos en bloques entre varios DataNodes, con NameNode centralizado para la gestión de metadatos y replicación automática de bloques.

---

## Arquitectura

- **NameNode**: Gestiona metadatos, directorios, asignación y replicación de bloques.
- **DataNode**: Almacena bloques de archivos y replica bloques entre nodos.
- **Cliente (CLI)**: Permite a los usuarios interactuar con el DFS mediante comandos tipo Unix.

La comunicación entre componentes utiliza:
- **REST API**: Canal de control (NameNode <-> Cliente)
- **gRPC**: Canal de datos (Cliente <-> DataNode, DataNode <-> DataNode)

### Diagrama Simplificado
```
Cliente 1 (CLI)         Cliente n (CLI)
      |                      |
      |--- REST API -------->|
      |                      |
   NameNode (Control)        |
      |                      |
      |--- gRPC -------------|
      |                      |
   DataNode-1 ... DataNode-N (Datos y replicación)
```

---

## Estructura de Archivos

```
proyecto2sd/
│
├── config/                  # Configuración del clúster y nodos
│   ├── cluster_config.yaml
│   └── development.json
│
├── scripts/                 # Scripts de despliegue y utilidades
│   ├── deploy_cluster.sh
│   ├── start_cluster.sh
│   ├── generate_grpc.sh
│   └── check_cluster.sh
│
├── src/
│   ├── client/              # Cliente CLI
│   │   └── cli.py
│   ├── common/              # Configuración y utilidades compartidas
│   │   └── config.py
│   ├── datanode/            # Lógica de DataNode
│   │   └── server.py
│   ├── namenode/            # Lógica de NameNode
│   │   └── server.py
│   └── proto/               # Definiciones gRPC y protobuf
│       ├── dfs.proto
│       ├── dfs_pb2.py
│       └── dfs_pb2_grpc.py
│
├── requirements.txt         # Dependencias Python
├── setup.py                 # Instalador del paquete
├── ejecucion.txt            # Lista de comandos usados a mano sobre maquinas AWS (nodos)
└── README.md                # Este archivo
```

---

## Instalación y Despliegue

### Requisitos
- Python 3.11+
- Git
- Acceso a varias instancias (para pruebas distribuidas)

### Pasos rápidos
```bash
# Clonar el repositorio
git clone https://github.com/Cardanivelez/proyecto2sd.git
cd proyecto2sd

# Crear entorno virtual
python3.11 -m venv env
source env/bin/activate

# Instalar dependencias
python3 -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Generar código gRPC
./scripts/generate_grpc.sh
```

### Despliegue automático
Utiliza el script `scripts/deploy_cluster.sh` para desplegar el clúster en múltiples nodos.

---

## Comandos del Cliente (CLI)
El cliente implementa comandos similares a Unix:
- `ls`      : Lista el contenido de un directorio
- `cd`      : Cambia el directorio actual
- `mkdir`   : Crea un nuevo directorio
- `rmdir`   : Elimina un directorio
- `rm`      : Elimina un archivo
- `put`     : Sube un archivo al DFS
- `get`     : Descarga un archivo del DFS
- `pwd`     : Muestra el directorio actual en el DFS

Ejemplo de uso:
```bash
python -m src.client.cli ls
python -m src.client.cli put archivo.txt /carpeta/archivo.txt
```

---

## Especificaciones Técnicas
- **Particionado por bloques**: Cada archivo se divide en bloques distribuidos entre DataNodes.
- **Replicación**: Cada bloque se replica al menos en dos DataNodes para tolerancia a fallos.
- **Algoritmo de distribución**: El NameNode selecciona DataNodes óptimos según métricas de carga y espacio.
- **Canal de control**: REST API para metadatos y operaciones de directorio.
- **Canal de datos**: gRPC para transferencia eficiente de bloques.
- **WORM**: El sistema es Write-Once-Read-Many, no permite modificaciones parciales de archivos.

---

## Referencias y Lecturas Recomendadas
- [Google File System (GFS)](https://g.co/kgs/XzwmU76)
- [Hadoop Distributed File System (HDFS)](https://es.wikipedia.org/wiki/Hadoop_Distributed_File_System)

---

## Créditos
Proyecto desarrollado para la asignatura Arquitectura de Nube y Sistemas Distribuidos, UPB 2025.
