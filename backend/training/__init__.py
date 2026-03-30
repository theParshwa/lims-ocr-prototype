"""Training examples module — few-shot context for LLM extraction."""
from .training_manager import TrainingManager
from .excel_parser import parse_training_excel, build_training_prompt_context

__all__ = ["TrainingManager", "parse_training_excel", "build_training_prompt_context"]
