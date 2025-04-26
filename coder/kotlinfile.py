from pydantic import BaseModel, Field


class UITestsKotlinFile(BaseModel):
    """Model of kotlin file.kt from android ui autotests project"""
    relative_filepath: str = Field(description="Relative to project path to file")
    source: str = Field(description="File sourcecode")