from typing import Dict, Any

class ComplexityBudget:
    """
    Centralized Complexity Governance & Hard Control Limits (Phases 16-17).
    Enforces absolute bounds across all control plane paths to prevent recursive collapse.
    """
    MAX_GOVERNANCE_LAYERS = 8
    MAX_MUTATION_DEPTH = 3
    MAX_REPLAY_DEPTH = 5
    MAX_DEPENDENCY_DEPTH = 5
    MAX_MEMORY_CHAIN_LENGTH = 10
    MAX_CROSS_WORKFLOW_REFERENCES = 10
    MAX_TELEMETRY_RECURSION = 3

    @staticmethod
    def validate_governance_layers(layers: int) -> bool:
        return layers <= ComplexityBudget.MAX_GOVERNANCE_LAYERS

    @staticmethod
    def validate_mutation_depth(depth: int) -> bool:
        return depth <= ComplexityBudget.MAX_MUTATION_DEPTH

    @staticmethod
    def validate_replay_depth(depth: int) -> bool:
        return depth <= ComplexityBudget.MAX_REPLAY_DEPTH

    @staticmethod
    def validate_dependency_depth(depth: int) -> bool:
        return depth <= ComplexityBudget.MAX_DEPENDENCY_DEPTH

    @staticmethod
    def validate_memory_chain(chain_len: int) -> bool:
        return chain_len <= ComplexityBudget.MAX_MEMORY_CHAIN_LENGTH

    @staticmethod
    def validate_cross_workflow_references(ref_count: int) -> bool:
        return ref_count <= ComplexityBudget.MAX_CROSS_WORKFLOW_REFERENCES

    @staticmethod
    def validate_telemetry_recursion(depth: int) -> bool:
        return depth <= ComplexityBudget.MAX_TELEMETRY_RECURSION

    @staticmethod
    def validate_all(metrics: Dict[str, int]) -> Dict[str, Any]:
        """
        Validates a dictionary of metric values against the corresponding budget limits.
        """
        validation = {}
        if "governance_layers" in metrics:
            validation["governance_layers"] = ComplexityBudget.validate_governance_layers(metrics["governance_layers"])
        if "mutation_depth" in metrics:
            validation["mutation_depth"] = ComplexityBudget.validate_mutation_depth(metrics["mutation_depth"])
        if "replay_depth" in metrics:
            validation["replay_depth"] = ComplexityBudget.validate_replay_depth(metrics["replay_depth"])
        if "dependency_depth" in metrics:
            validation["dependency_depth"] = ComplexityBudget.validate_dependency_depth(metrics["dependency_depth"])
        if "memory_chain_length" in metrics:
            validation["memory_chain_length"] = ComplexityBudget.validate_memory_chain(metrics["memory_chain_length"])
        if "cross_workflow_references" in metrics:
            validation["cross_workflow_references"] = ComplexityBudget.validate_cross_workflow_references(metrics["cross_workflow_references"])
        if "telemetry_recursion" in metrics:
            validation["telemetry_recursion"] = ComplexityBudget.validate_telemetry_recursion(metrics["telemetry_recursion"])
            
        validation["all_passed"] = all(validation.values())
        return validation
