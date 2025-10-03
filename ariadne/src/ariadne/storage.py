"""
File-based storage for process models.
"""

import json
from pathlib import Path
from typing import Optional

from ariadne.domain.models.process_model import EndpointModel


class ModelStorage:
    """
    Simple file-based storage for process models.

    Directory structure:
        models/
        ├── service1/
        │   ├── endpoint1/
        │   │   ├── model.json
        │   │   └── metadata.json
        │   └── endpoint2/
        │       ├── model.json
        │       └── metadata.json
        └── service2/
            └── ...
    """

    def __init__(self, base_path: Path):
        """
        Initialize storage at the given base path.

        Args:
            base_path: Root directory for model storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_model_dir(self, service_name: str, endpoint_name: str) -> Path:
        """Get the directory path for a specific endpoint's model."""
        # Sanitize names for filesystem
        service_clean = self._sanitize_name(service_name)
        endpoint_clean = self._sanitize_name(endpoint_name)

        model_dir = self.base_path / service_clean / endpoint_clean
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize name for use in filesystem paths."""
        # Replace problematic characters
        return name.replace("/", "_").replace("\\", "_").replace(":", "_")

    def ensure_empty(self):
        """Ensure the storage directory is empty."""
        if self.base_path.exists():
            import shutil

            shutil.rmtree(self.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        service_name: str,
        endpoint_name: str,
        model: EndpointModel,
        algorithm: str,
        metadata: Optional[dict] = None,
    ):
        """
        Save a process model to disk.

        Args:
            service_name: Name of the service
            endpoint_name: Name of the endpoint/operation
            model: The process model object
            algorithm: Name of the algorithm used
            miner: The miner instance (used for serialization)
            metadata: Optional additional metadata
        """
        model_dir = self._get_model_dir(service_name, endpoint_name)

        # Save model
        model_path = model_dir / "model.pnml"
        with open(model_path, "w") as f:
            f.write(model.pnml_content)

        # Save model visualization
        dot_path = model_dir / "model.dot"
        with open(dot_path, "w") as f:
            f.write(model.dot_content)

        # Save metadata
        meta = {
            "service_name": service_name,
            "endpoint_name": endpoint_name,
            "algorithm": algorithm,
            **(metadata or {}),
        }

        meta_path = model_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def load_model(
        self, service_name: str, endpoint_name: str
    ) -> Optional[EndpointModel]:
        """
        Load a process model from disk.

        Args:
            service_name: Name of the service
            endpoint_name: Name of the endpoint/operation
            algorithm: Name of the algorithm used
            miner: The miner instance (used for deserialization)

        Returns:
            The deserialized model, or None if not found
        """
        model_dir = self._get_model_dir(service_name, endpoint_name)
        model_path = model_dir / "model.pnml"

        if not model_path.exists():
            return None

        with open(model_path) as f:
            model = f.read()

        dot_path = model_dir / "model.dot"
        with open(dot_path) as f:
            dot_content = f.read()

        return EndpointModel(pnml_content=model, dot_content=dot_content)

    def list_models(self) -> list[tuple[str, str]]:
        """
        List all available models.

        Returns:
            List of (service_name, endpoint_name) tuples
        """
        models = []

        for service_dir in self.base_path.iterdir():
            if not service_dir.is_dir():
                continue

            for endpoint_dir in service_dir.iterdir():
                if not endpoint_dir.is_dir():
                    continue

                # Check if it has a model
                if (endpoint_dir / "model.pnml").exists():
                    # Read actual names from metadata
                    meta_path = endpoint_dir / "metadata.json"
                    if meta_path.exists():
                        with open(meta_path) as f:
                            meta = json.load(f)
                            models.append((meta["service_name"], meta["endpoint_name"]))
                    else:
                        # Fallback to directory names
                        models.append((service_dir.name, endpoint_dir.name))

        return models

    def delete_model(self, service_name: str, endpoint_name: str):
        """Delete a model from storage."""
        model_dir = self._get_model_dir(service_name, endpoint_name)

        if model_dir.exists():
            import shutil

            shutil.rmtree(model_dir)
