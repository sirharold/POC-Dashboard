"""
Utility to load available.log paths from Parameters JSON files.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class ParametersLoader:
    """Loads and manages VM parameters from JSON files."""

    def __init__(self, parameters_dir: str = None):
        """Initialize with the Parameters directory path."""
        if parameters_dir is None:
            # Default to Parameters directory in project root
            project_root = Path(__file__).parent.parent
            parameters_dir = os.path.join(project_root, "Parameters")

        self.parameters_dir = parameters_dir
        self._cache = {}

    def _load_all_parameters(self) -> Dict[str, dict]:
        """Load all parameter files and cache them."""
        if self._cache:
            return self._cache

        parameters = {}

        try:
            # Get all JSON files in Parameters directory
            param_files = Path(self.parameters_dir).glob("Params_*.json")

            for param_file in param_files:
                with open(param_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    vms = data.get('vms', [])

                    # Index by instance_id
                    for vm in vms:
                        instance_id = vm.get('instance_id')
                        if instance_id:
                            parameters[instance_id] = vm

            self._cache = parameters
        except Exception as e:
            print(f"Error loading parameters: {e}")

        return parameters

    def get_available_log_paths(self, instance_id: str) -> List[str]:
        """Get available.log paths for a specific instance."""
        params = self._load_all_parameters()
        vm_data = params.get(instance_id, {})
        return vm_data.get('paths', [])

    def get_instance_info(self, instance_id: str) -> Optional[dict]:
        """Get full instance information including name, os_type, and paths."""
        params = self._load_all_parameters()
        return params.get(instance_id)

    def get_os_type(self, instance_id: str) -> str:
        """Get OS type for an instance (linux or windows)."""
        vm_info = self.get_instance_info(instance_id)
        if vm_info:
            return vm_info.get('os_type', 'linux')
        return 'linux'  # Default fallback
