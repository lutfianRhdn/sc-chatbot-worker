from typing import TypedDict, Optional, List


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents
    """

    question: str
    generation: str
    web_search: str
    documents: List[str]
    key_word: str
    grade: str
    evidence: List[str]
    claim : str
    previous_opinion: str
    round_count: int
    question: str
    final_decision: Optional[str]