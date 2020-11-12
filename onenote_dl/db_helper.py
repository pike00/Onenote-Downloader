import pandas as pd
import sqlalchemy as db
from hashable_df import hashable_df
from sqlalchemy import String, Column, Table
from sqlalchemy.ext.declarative import declarative_base

from definitions import DATABASE_PATH
from onenote_classes.onenoteobject import *

print("In DB Helper")
engine = db.create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
connection = engine.connect()

Base = declarative_base()


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(String, primary_key=True)
    createdDateTime = Column(String)
    displayName = Column(String)
    lastModifiedDateTime = Column(String)

    def __str__(self) -> str:
        return f"Notebook: {self.displayName} ({self.id})"


sections_table = Table(
    "sections",
    Base.metadata,
    Column("id", String, primary_key=True),
    Column("createdDateTime", String),
    Column("displayName", String),
    Column("lastModifiedDateTime", String),
    Column("parentNotebookID", String)
)

pages_table = Table(
    "pages",
    Base.metadata,
    Column("id", String, primary_key=True),
    Column("createdDateTime", String),
    Column("displayName", String),
    Column("lastModifiedDateTime", String),
    Column("parentNotebookID", String)
)

Base.metadata.create_all(engine)


class OneNoteType(Enum):
    NOTEBOOK = "notebooks"
    SECTION = "sections"
    PAGE = "pages"

    tableName: str

    # ASSET = "assets"

    def __init__(self, tableName) -> None:
        super().__init__()
        self.tableName = tableName


# print("id db helper")


# Saves data to table in database, connecting if necessary
def save_table_to_db(dataFrame, tableName, overwrite=False):
    connect_to_db()

    # IF overwrite is positive, erase old data and re-write in place
    if overwrite:
        dataFrame.to_sql(tableName, connection, if_exists='replace', index=False)
    # Otherwise, if the table_exists, read the old data and combine , dropping duplicates
    elif table_exists(tableName):
        old_df = read_table_from_sql(tableName)
        combined_df = hashable_df(pd.concat([old_df, dataFrame], ignore_index=True)).drop_duplicates()

        # Serialize
        combined_df.to_sql(tableName, connection, if_exists='replace', index=False)
    else:  # Overwrite is false, and table doesn't exist
        # Write to sql for the first time
        # if_exists='fail' is just a double check, and shouldn't ever fail based on the logic above
        dataFrame.to_sql(tableName, connection, if_exists='fail', index=False)


def add_entry(dataFrame, tableName):
    connect_to_db()


def close_connection_to_db():
    connection.close()


def parseJSON(json_content, objectType: OneNoteType):
    params = {}

    for key, value in {'id': 'id',
                       'createdDateTime': 'createdDateTime',
                       'lastModifiedDateTime': 'lastModifiedDateTime'}.items():
        params[key] = json_content[value]

    if objectType == OneNoteType.NOTEBOOK:
        params['displayName'] = json_content.get('displayName')

        return Notebook(**params)
    elif objectType == OneNoteType.SECTION:
        params['displayName'] = json_content.get('displayName')
        params['parentNotebookID'] = json_content.get('parentNotebook').get('id')
    elif objectType == OneNoteType.PAGE:
        params['displayName'] = json_content.get('title')
        params['parentSectionID'] = json_content.get('parentSection').get('id')

    return
