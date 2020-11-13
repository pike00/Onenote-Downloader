from enum import Enum

import pandas as pd
from hashable_df import hashable_df
import sqlalchemy as db
from sqlalchemy import String, Column, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from definitions import DATABASE_PATH

engine = db.create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
connection = engine.connect()

session = Session(bind=engine)

Base = declarative_base()


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(String, primary_key=True)
    createdDateTime = Column(String)
    displayName = Column(String)
    lastModifiedDateTime = Column(String)

    def get_dictionary(self):
        return {'id': self.id,
                'createdDateTime': self.createdDateTime,
                'displayName': self.displayName,
                'lastModifiedDateTime': self.lastModifiedDateTime}

    def __str__(self) -> str:
        return f"Notebook: {self.displayName} ({self.id})"


class Section(Base):
    __tablename__ = "sections"

    id = Column(String, primary_key=True)
    createdDateTime = Column(String)
    displayName = Column(String)
    lastModifiedDateTime = Column(String)
    parentNotebookID = Column(String)

    def get_dictionary(self):
        return {'id': self.id,
                'createdDateTime': self.createdDateTime,
                'displayName': self.displayName,
                'lastModifiedDateTime': self.lastModifiedDateTime,
                'parentNotebookID': self.parentNotebookID}

    def __str__(self) -> str:
        return f"Section: {self.displayName} ({self.id})"

class Page(Base):
    __tablename__ = "pages"

    id = Column(String, primary_key=True)
    createdDateTime = Column(String)
    displayName = Column(String)
    lastModifiedDateTime = Column(String)
    parentSectionID = Column(String)

    def get_dictionary(self):
        return {'id': self.id,
                'createdDateTime': self.createdDateTime,
                'displayName': self.displayName,
                'lastModifiedDateTime': self.lastModifiedDateTime,
                'parentSectionID': self.parentSectionID}

    def __str__(self) -> str:
        return f"Page: {self.displayName} ({self.id})"


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

        return Section(**params)
    elif objectType == OneNoteType.PAGE:
        params['displayName'] = json_content.get('title')
        params['parentSectionID'] = json_content.get('parentSection').get('id')

        return Page(**params)


def update_row(onenoteobject):
    onenoteobjectclass = onenoteobject.__class__
    results = session.query(onenoteobjectclass).filter(onenoteobjectclass.id == onenoteobject.id)
    if results.count() == 1:
        results.update(onenoteobject.get_dictionary())
    elif results.count() == 0:
        session.add(onenoteobject)
    else:
        raise IndexError(f"More than one row exists for this Object id {onenoteobject.id} (Class: {onenoteobjectclass}")

    session.commit()

# def update_section(section):
#     results = session.query(Section).filter(Section.id == section.id)
#     if results.count() == 1:
#         old_notebook = results.first()
#         old_notebook.createdDateTime = notebook.createdDateTime
#         old_notebook.displayName = notebook.displayName
#         old_notebook.lastModifiedDateTime = notebook.lastModifiedDateTime
#     elif results.count() == 0:
#         session.add(notebook)
#     else:
#         raise IndexError(f"More than one row exists for this Notebook id {notebook.id}")
#
#     session.commit()
