"""Plain dataclasses: Temporal's default data converter serialises them to JSON."""

from dataclasses import dataclass, field

TASK_QUEUE = "grant-review"


@dataclass
class Application:
    id: str
    applicant: str
    postcode: str
    amount_requested: int  # whole pounds
    title: str
    summary: str


@dataclass
class Eligibility:
    eligible: bool
    reasons: list[str] = field(default_factory=list)  # why not, when ineligible


@dataclass
class Score:
    community_benefit: int  # each 1-5
    feasibility: int
    value_for_money: int
    rationale: str

    @property
    def total(self) -> int:
        return self.community_benefit + self.feasibility + self.value_for_money


@dataclass
class Review:
    application_id: str
    decision: str  # "approved" | "declined"
    letter: str
    score: Score | None = None
    eligibility_reasons: list[str] = field(default_factory=list)
