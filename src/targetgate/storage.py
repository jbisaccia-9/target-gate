"""Snapshot storage: an Azure Blob container in production, a local directory
everywhere else - same interface, chosen by environment.

Live mode uses azure-storage-blob against AZURE_STORAGE_CONNECTION_STRING
(container name in config). Local mode writes ./container/, which is what the
tests, CI, and any keyless clone exercise. The pipeline code cannot tell the
difference, which is the point.
"""
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


class LocalContainer:
    def __init__(self, name="container"):
        self.path = ROOT / name
        self.path.mkdir(exist_ok=True)

    def put(self, blob_name, data):
        (self.path / blob_name).write_text(json.dumps(data, indent=2))

    def get(self, blob_name):
        return json.loads((self.path / blob_name).read_text())

    def exists(self, blob_name):
        return (self.path / blob_name).exists()


class AzureContainer:
    """Thin adapter over azure-storage-blob; requires the azure extra."""
    def __init__(self, name):
        from azure.storage.blob import BlobServiceClient  # deferred import
        svc = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"])
        self.client = svc.get_container_client(name)
        if not self.client.exists():
            self.client.create_container()

    def put(self, blob_name, data):
        self.client.upload_blob(blob_name, json.dumps(data), overwrite=True)

    def get(self, blob_name):
        return json.loads(self.client.download_blob(blob_name).readall())

    def exists(self, blob_name):
        return self.client.get_blob_client(blob_name).exists()


def get_container(name="provider-snapshots"):
    if os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        return AzureContainer(name)
    return LocalContainer()
