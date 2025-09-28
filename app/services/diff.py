# app/services/diff.py
"""
Deep JSON diff service for comparing document versions and extractions
"""
from typing import Dict, Any, List, Set
import json
import logging

logger = logging.getLogger(__name__)


class DiffService:
    """Service for performing deep JSON diffs"""
    
    @staticmethod
    def deep_diff(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform deep comparison of two JSON objects"""
        
        result = {
            "added": {},
            "removed": {},
            "changed": {},
            "unchanged": {}
        }
        
        # Get all keys from both objects
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # Find added keys
        added_keys = new_keys - old_keys
        for key in added_keys:
            result["added"][key] = new_data[key]
        
        # Find removed keys
        removed_keys = old_keys - new_keys
        for key in removed_keys:
            result["removed"][key] = old_data[key]
        
        # Find changed/unchanged keys
        common_keys = old_keys & new_keys
        for key in common_keys:
            old_value = old_data[key]
            new_value = new_data[key]
            
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                # Recursive diff for nested objects
                nested_diff = DiffService.deep_diff(old_value, new_value)
                if DiffService._has_changes(nested_diff):
                    result["changed"][key] = nested_diff
                else:
                    result["unchanged"][key] = new_value
            elif isinstance(old_value, list) and isinstance(new_value, list):
                # Array comparison
                array_diff = DiffService._compare_arrays(old_value, new_value)
                if array_diff:
                    result["changed"][key] = array_diff
                else:
                    result["unchanged"][key] = new_value
            else:
                # Simple value comparison
                if old_value != new_value:
                    result["changed"][key] = {
                        "old": old_value,
                        "new": new_value
                    }
                else:
                    result["unchanged"][key] = new_value
        
        return result
    
    @staticmethod
    def _has_changes(diff_result: Dict[str, Any]) -> bool:
        """Check if diff result contains any changes"""
        return bool(diff_result["added"] or diff_result["removed"] or diff_result["changed"])
    
    @staticmethod
    def _compare_arrays(old_array: List[Any], new_array: List[Any]) -> Dict[str, Any]:
        """Compare two arrays and return differences"""
        if len(old_array) != len(new_array):
            return {
                "type": "array_length_changed",
                "old_length": len(old_array),
                "new_length": len(new_array),
                "old": old_array,
                "new": new_array
            }
        
        changes = {}
        for i, (old_item, new_item) in enumerate(zip(old_array, new_array)):
            if isinstance(old_item, dict) and isinstance(new_item, dict):
                item_diff = DiffService.deep_diff(old_item, new_item)
                if DiffService._has_changes(item_diff):
                    changes[f"index_{i}"] = item_diff
            elif old_item != new_item:
                changes[f"index_{i}"] = {
                    "old": old_item,
                    "new": new_item
                }
        
        return changes if changes else None
    
    @staticmethod
    def compare_documents(doc1_data: Dict[str, Any], doc2_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two document extraction results"""
        
        comparison = {
            "summary": {
                "total_changes": 0,
                "added_fields": 0,
                "removed_fields": 0,
                "modified_fields": 0
            },
            "details": DiffService.deep_diff(doc1_data, doc2_data),
            "metadata": {
                "comparison_timestamp": DiffService._get_timestamp(),
                "doc1_keys_count": len(doc1_data.keys()),
                "doc2_keys_count": len(doc2_data.keys())
            }
        }
        
        # Calculate summary statistics
        details = comparison["details"]
        comparison["summary"]["added_fields"] = len(details["added"])
        comparison["summary"]["removed_fields"] = len(details["removed"])
        comparison["summary"]["modified_fields"] = len(details["changed"])
        comparison["summary"]["total_changes"] = (
            comparison["summary"]["added_fields"] + 
            comparison["summary"]["removed_fields"] + 
            comparison["summary"]["modified_fields"]
        )
        
        return comparison
    
    @staticmethod
    def extract_concrete_changes(diff_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract concrete-specific changes from diff result"""
        
        concrete_fields = [
            "concrete_grade", "grades", "volumes", "construction_elements",
            "concrete_classes", "exposure_classes", "strength_class"
        ]
        
        concrete_changes = {
            "concrete_added": {},
            "concrete_removed": {},
            "concrete_modified": {},
            "other_changes": {
                "added": {},
                "removed": {},
                "changed": {}
            }
        }
        
        # Separate concrete-related changes from other changes
        for change_type in ["added", "removed", "changed"]:
            changes = diff_result.get(change_type, {})
            
            for key, value in changes.items():
                if any(concrete_field in key.lower() for concrete_field in concrete_fields):
                    concrete_changes[f"concrete_{change_type}"][key] = value
                else:
                    concrete_changes["other_changes"][change_type][key] = value
        
        return concrete_changes
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    @staticmethod
    def generate_diff_summary(diff_result: Dict[str, Any]) -> str:
        """Generate human-readable summary of changes"""
        
        summary_parts = []
        
        added_count = len(diff_result.get("added", {}))
        if added_count > 0:
            summary_parts.append(f"{added_count} fields added")
        
        removed_count = len(diff_result.get("removed", {}))
        if removed_count > 0:
            summary_parts.append(f"{removed_count} fields removed")
        
        changed_count = len(diff_result.get("changed", {}))
        if changed_count > 0:
            summary_parts.append(f"{changed_count} fields modified")
        
        if not summary_parts:
            return "No changes detected"
        
        return ", ".join(summary_parts)