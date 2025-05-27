import typer
import requests
import grpc
import asyncio
import os
from pathlib import Path
from typing import Optional
from ..proto import dfs_pb2, dfs_pb2_grpc
from ..common.config import Config

app = typer.Typer()
config = Config.load()
SESSION_PATH_FILE = os.path.expanduser("~/.dfs_client_path")

def load_current_path():
    if os.path.exists(SESSION_PATH_FILE):
        with open(SESSION_PATH_FILE, 'r') as f:
            return f.read().strip() or "/"
    return "/"

def save_current_path(path):
    with open(SESSION_PATH_FILE, 'w') as f:
        f.write(path)

current_path = load_current_path()

@app.command()
def ls(path: Optional[str] = None):
    """Lista el contenido de un directorio"""
    target_path = path if path else current_path
    response = requests.get(f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/ls/{target_path}")
    if response.status_code == 200:
        contents = response.json()["contents"]
        for name, type_ in contents.items():
            if type_ == "file":
                typer.echo(f"FILE\t{name}")
            else:
                typer.echo(f"DIR\t{name}/")
    else:
        typer.echo(f"Error: {response.json()['detail']}")

@app.command()
def cd(path: str):
    """Cambia el directorio actual"""
    global current_path
    if path.startswith("/"):
        new_path = path
    else:
        new_path = str(Path(current_path) / path)
    
    response = requests.get(f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/ls/{new_path}")
    if response.status_code == 200:
        current_path = new_path
        save_current_path(current_path)
        typer.echo(f"Directorio actual: {current_path}")
    else:
        typer.echo(f"Error: Directorio no encontrado")

@app.command()
def mkdir(path: str):
    """Crea un nuevo directorio"""
    if not path.startswith("/"):
        path = str(Path(current_path) / path)
    
    response = requests.post(
        f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/directory",
        params={"path": path}
    )
    if response.status_code == 200:
        typer.echo(f"Directorio creado: {path}")
    else:
        typer.echo(f"Error: {response.json()['detail']}")

@app.command()
def rmdir(path: str):
    """Elimina un directorio"""
    if not path.startswith("/"):
        path = str(Path(current_path) / path)
    
    response = requests.delete(
        f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/directory",
        params={"path": path}
    )
    if response.status_code == 200:
        typer.echo(f"Directorio eliminado: {path}")
    else:
        typer.echo(f"Error: {response.json()['detail']}")

@app.command()
def rm(path: str):
    """Elimina un archivo"""
    if not path.startswith("/"):
        path = str(Path(current_path) / path)
    
    response = requests.delete(
        f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/files",
        params={"path": path}
    )
    if response.status_code == 200:
        typer.echo(f"Archivo eliminado: {path}")
    else:
        typer.echo(f"Error: {response.json()['detail']}")

@app.command()
def put(local_path: str, dfs_path: str):
    """Sube un archivo al DFS"""
    if not dfs_path.startswith("/"):
        dfs_path = str(Path(current_path) / dfs_path)
    
    file_size = Path(local_path).stat().st_size
    
    # Solicitar asignación de bloques al NameNode
    response = requests.post(
        f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/files",
        params={"filename": dfs_path, "size": file_size}
    )
    
    if response.status_code != 200:
        typer.echo(f"Error: {response.json()['detail']}")
        return
    
    blocks = response.json()["blocks"]
    
    # Transferir bloques a los DataNodes
    with open(local_path, 'rb') as f:
        for block in blocks:
            # Conectar con el leader DataNode
            channel = grpc.insecure_channel(block["leader"]["address"])
            stub = dfs_pb2_grpc.FileServiceStub(channel)
            
            # Leer y enviar el bloque
            chunk_size = config.BLOCK_SIZE
            while chunk := f.read(chunk_size):
                response = stub.PutBlock(iter([
                    dfs_pb2.BlockData(
                        block_id=block["block_id"],
                        data=chunk,
                        replica_nodes=[node["address"] for node in block["followers"]]
                    )
                ]))
                
                if not response.success:
                    typer.echo(f"Error al escribir bloque: {response.message}")
                    return

    typer.echo(f"Archivo subido exitosamente: {dfs_path}")

@app.command()
def get(dfs_path: str, local_path: str):
    """Descarga un archivo del DFS"""
    if not dfs_path.startswith("/"):
        dfs_path = str(Path(current_path) / dfs_path)
    
    # Obtener metadata del archivo
    response = requests.get(
        f"http://{config.NAMENODE_HOST}:{config.NAMENODE_PORT}/files/{dfs_path}"
    )
    
    if response.status_code != 200:
        typer.echo(f"Error: {response.json()['detail']}")
        return
    
    file_info = response.json()
    
    # Descargar bloques
    with open(local_path, 'wb') as f:
        for block in file_info["blocks"]:
            # Intentar con el leader primero
            success = False
            nodes = [block["leader"]] + block["followers"]
            
            for node in nodes:
                try:
                    channel = grpc.insecure_channel(node["address"])
                    stub = dfs_pb2_grpc.FileServiceStub(channel)
                    
                    # Obtener bloque
                    response = stub.GetBlock(dfs_pb2.BlockRequest(
                        block_id=block["block_id"]
                    ))
                    
                    # Escribir datos
                    for chunk in response:
                        f.write(chunk.data)
                    
                    success = True
                    break
                except Exception as e:
                    continue
            
            if not success:
                typer.echo(f"Error: No se pudo recuperar el bloque {block['block_id']}")
                return

    typer.echo(f"Archivo descargado exitosamente: {local_path}")

@app.command()
def pwd():
    """Muestra el directorio actual en el DFS"""
    global current_path
    current_path = load_current_path()
    typer.echo(f"Directorio actual: {current_path}")

# Cambio para forzar commit en git

if __name__ == "__main__":
    app()