#!/bin/bash

# Generar código Python desde el archivo .proto
python -m grpc_tools.protoc \
    -I./src/proto \
    --python_out=./src/proto \
    --grpc_python_out=./src/proto \
    ./src/proto/dfs.proto

# Corregir imports en los archivos generados
sed -i 's/import dfs_pb2/from . import dfs_pb2/' src/proto/dfs_pb2_grpc.py