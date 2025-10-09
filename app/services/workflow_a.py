async def run(
        self,
        file_path: Path,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run complete Workflow A (backward compatibility)
        
        This method provides backward compatibility with the old API.
        It calls the new simplified workflow methods.
        
        Args:
            file_path: Path to document file
            project_name: Name of the project
        
        Returns:
            Audit results
        """
        try:
            logger.info(f"Starting Workflow A (compatibility mode) for: {file_path}")
            
            # Step 1: Import and prepare all positions
            import_result = await self.import_and_prepare(file_path, project_name)
            
            if not import_result.get("success"):
                return import_result
            
            positions = import_result.get("positions", [])
            
            if not positions:
                logger.warning("No positions to audit")
                return {
                    "success": False,
                    "error": "No positions found in document",
                    "positions": []
                }
            
            # Step 2: For backward compatibility, analyze ALL positions
            # (In new workflow, user selects which positions to analyze)
            logger.info(f"Auto-analyzing all {len(positions)} positions for compatibility")
            
            position_ids = [i for i in range(len(positions))]
            
            # Step 3: Analyze selected positions
            audit_result = await self.analyze_selected_positions(
                positions=positions,
                selected_indices=position_ids,
                project_context=import_result.get("project_context", {})
            )
            
            # Step 4: Add summary statistics
            categorized = self._categorize_results(audit_result.get("results", []))
            summary = self._generate_summary(categorized)
            
            return {
                "success": True,
                "project_name": project_name,
                "total_positions": len(positions),
                "analyzed_positions": len(position_ids),
                "summary": summary,
                "positions": categorized,
                "hitl_positions": [p for p in audit_result.get("results", []) 
                                  if p.get("hitl_required")],
                "audit_results": audit_result
            }
            
        except Exception as e:
            logger.error(f"Workflow A failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "positions": []
            }
    
    def _categorize_results(
        self,
        audit_results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize audit results by classification
        
        Args:
            audit_results: List of audit results
        
        Returns:
            Dict with 'green', 'amber', 'red' keys
        """
        categorized = {
            'green': [],
            'amber': [],
            'red': []
        }
        
        for result in audit_results:
            classification = result.get('classification', 'AMBER').upper()
            
            if classification == 'GREEN':
                categorized['green'].append(result)
            elif classification == 'RED':
                categorized['red'].append(result)
            else:
                categorized['amber'].append(result)
        
        return categorized
    
    def _generate_summary(
        self,
        categorized: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics
        
        Args:
            categorized: Categorized results
        
        Returns:
            Summary dict
        """
        total = sum(len(v) for v in categorized.values())
        
        return {
            "total_positions": total,
            "green_count": len(categorized['green']),
            "amber_count": len(categorized['amber']),
            "red_count": len(categorized['red']),
            "green_percent": len(categorized['green']) / total * 100 if total > 0 else 0,
            "amber_percent": len(categorized['amber']) / total * 100 if total > 0 else 0,
            "red_percent": len(categorized['red']) / total * 100 if total > 0 else 0
        }
# ========================================
# Singleton instance for backward compatibility
# ========================================
workflow_a = WorkflowA()