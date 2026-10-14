"""The typed record the agent must produce."""

from typing import Optional

from pydantic import BaseModel, Field


class FoundItemRecord(BaseModel):
    """One found item, as logged by the Marlowe Hall lost-and-found desk."""

    item_type: str = Field(description="What the item is, in a word or two (umbrella, phone, scarf)")
    color: Optional[str] = Field(None, description="Main color, only if the note states one")
    brand: Optional[str] = Field(None, description="Brand or maker, only if the note names one")
    found_where: Optional[str] = Field(None, description="Where in the hall it was found")
    found_when: Optional[str] = Field(None, description="When it was found, as the note words it")
    finder_name: Optional[str] = Field(None, description="Name of the staff member or guest who handed it in")
    finder_contact: Optional[str] = Field(None, description="Phone or email of the finder, if written down")
    distinguishing_marks: Optional[str] = Field(
        None, description="Engravings, stickers, damage or contents that identify the owner"
    )
